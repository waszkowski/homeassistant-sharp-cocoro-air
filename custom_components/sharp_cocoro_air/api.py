"""Sharp Cocoro Air (EU) API client."""

from __future__ import annotations

import json
import logging
import re
import secrets
from dataclasses import dataclass, field
from html import unescape
from urllib.parse import urlencode, urljoin, urlparse, parse_qs

import aiohttp

from .const import (
    EPC_EXTENDED_STATUS,
    EPC_FAULT_STATUS,
    EPC_INSTANT_POWER,
    EPC_OPERATION_DETAIL,
    EPC_POWER,
    EPC_SENSOR_DATA,
    EPC_STATUS_FLAGS,
    F0_DUST_FILTER_LIMIT,
    F0_HUMID_FILTER_LIMIT,
    F0_ION_UNIT_LIMIT,
    F0_PCI_UNIT_LIMIT,
    F0_SMELL_FILTER_LIMIT,
    F1_AIR_QUALITY_OFFSET,
    F1_DUST_FILTER_USED,
    F1_HUMID_FILTER_USED,
    F1_HUMIDITY_OFFSET,
    F1_ION_UNIT_USED,
    F1_PARTICLES_OFFSET,
    F1_PCI_SENSOR_A,
    F1_PCI_SENSOR_B,
    F1_SMELL_FILTER_USED,
    F1_TEMPERATURE_OFFSET,
    F1_ZEROS,
    F2_DUST_LEVEL_BYTE,
    F2_LIGHT_DETECTED_BYTE,
    F2_ODOR_LEVEL_BYTE,
    F2_OVERALL_DIRT_BYTE,
    F2_WATER_TANK_BYTE,
    F2_ZEROS,
    F3_HUMID_BYTE,
    F3_MODE_BYTE,
    FAULT_OCCURRED,
    HMS_API_BASE,
    HMS_APP_SECRET,
    HMS_APP_SECRET_ENCODED,
    HMS_SERVICE_NAME,
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_REDIRECT_URI,
    OPERATION_MODES,
    OVERALL_DIRT_LEVELS,
    POWER_ON,
    TERMINAL_APP_NAME,
    TERMINAL_NAME,
    TERMINAL_OS,
    TERMINAL_OS_VERSION,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class ApiConnectionError(Exception):
    """Raised when API connection fails."""


@dataclass
class FilterLife:
    """Filter remaining life as percentages (0-100), None if unavailable."""

    hepa: int | None = None
    deodorizing: int | None = None
    humidifying: int | None = None
    ion_unit: int | None = None
    plasmacluster: int | None = None


@dataclass
class DeviceSensors:
    """Parsed sensor data for a single device."""

    power_on: bool | None = None
    fault: bool | None = None
    temperature: int | None = None
    humidity: int | None = None
    water_tank_full: bool | None = None
    operation_mode: str | None = None
    humidification_on: bool | None = None
    fine_particles: int | None = None
    air_quality: int | None = None
    odor_level: int | None = None
    dust_level: int | None = None
    overall_dirt: str | None = None
    light_detected: bool | None = None
    power_consumption_watts: int | None = None
    filters: FilterLife = field(default_factory=FilterLife)


@dataclass
class DeviceInfo:
    """Information about a Sharp Cocoro Air device."""

    box_id: str = ""
    device_id: int = 0
    model: str = ""
    maker: str = ""
    name: str = ""
    device_type: str = ""
    echonet_node: str = ""
    echonet_object: str = ""
    sensors: DeviceSensors = field(default_factory=DeviceSensors)
    raw_response: str = ""


def _parse_echonet_properties(hex_string: str) -> dict[int, bytes]:
    """Parse ECHONET Lite properties from hex-encoded string.

    Binary structure:
      Offset 0-6: 7-byte header
      Offset 7:   property count (1 byte)
      Offset 8+:  repeated: EPC(1) PDC(1) EDT(PDC bytes)
    """
    raw = bytes.fromhex(hex_string)
    if len(raw) < 9:
        return {}

    num_props = raw[7]
    offset = 8
    properties: dict[int, bytes] = {}

    for _ in range(num_props):
        if offset + 1 >= len(raw):
            break
        epc = raw[offset]
        pdc = raw[offset + 1]
        if offset + 2 + pdc > len(raw):
            break
        properties[epc] = raw[offset + 2 : offset + 2 + pdc]
        offset += 2 + pdc

    return properties


def _u16(data: bytes, offset: int) -> int:
    """Read 16-bit big-endian unsigned integer."""
    return data[offset] << 8 | data[offset + 1]


def _calc_filter_pct(limit: int, used: int) -> int | None:
    """Calculate filter remaining life percentage."""
    if limit <= 0:
        return None
    return max(0, min(100, (limit - used) * 100 // limit))


def _extract_sensors(properties: dict[int, bytes]) -> DeviceSensors:
    """Extract sensor values from parsed ECHONET properties."""
    sensors = DeviceSensors()

    # Power (0x80)
    if EPC_POWER in properties and len(properties[EPC_POWER]) >= 1:
        sensors.power_on = properties[EPC_POWER][0] == POWER_ON

    # Fault status (0x88) — per ECHONET spec: 0x41 = fault, 0x42 = no fault
    if EPC_FAULT_STATUS in properties and len(properties[EPC_FAULT_STATUS]) >= 1:
        sensors.fault = properties[EPC_FAULT_STATUS][0] == FAULT_OCCURRED

    # Instantaneous power consumption (0x84), big-endian uint, watts
    if EPC_INSTANT_POWER in properties and len(properties[EPC_INSTANT_POWER]) >= 1:
        sensors.power_consumption_watts = int.from_bytes(
            properties[EPC_INSTANT_POWER], "big"
        )

    # Sensor data F1 (temperature, humidity, fine particles)
    f1 = properties.get(EPC_SENSOR_DATA)
    if f1 and len(f1) > max(F1_TEMPERATURE_OFFSET, F1_HUMIDITY_OFFSET):
        sensors.temperature = f1[F1_TEMPERATURE_OFFSET]
        sensors.humidity = f1[F1_HUMIDITY_OFFSET]
    if f1 and len(f1) > F1_AIR_QUALITY_OFFSET + 1:
        # 10-bit value from 16-bit: bit15 = error, bits 0-9 = score 0-500
        val16 = f1[F1_AIR_QUALITY_OFFSET] << 8 | f1[F1_AIR_QUALITY_OFFSET + 1]
        if not (val16 & 0x8000):
            sensors.air_quality = min(val16 & 0x03FF, 500)
    if f1 and len(f1) > F1_PARTICLES_OFFSET + 2:
        # 24-bit big-endian: bit7 of byte[40] = error flag, bits 0-6 + byte[41] + byte[42] = value
        if not (f1[F1_PARTICLES_OFFSET] & 0x80):
            sensors.fine_particles = (
                (f1[F1_PARTICLES_OFFSET] & 0x7F) << 16
                | f1[F1_PARTICLES_OFFSET + 1] << 8
                | f1[F1_PARTICLES_OFFSET + 2]
            )

    # Operation mode + humidification from F3 property (Sharp proprietary)
    f3 = properties.get(EPC_OPERATION_DETAIL)
    if f3 and len(f3) > F3_MODE_BYTE:
        sensors.operation_mode = OPERATION_MODES.get(f3[F3_MODE_BYTE])
    if f3 and len(f3) > F3_HUMID_BYTE:
        sensors.humidification_on = f3[F3_HUMID_BYTE] == 0xFF

    # Status flags F2 (water tank, odor, dust, light)
    f2 = properties.get(EPC_STATUS_FLAGS)
    if f2:
        if len(f2) > F2_WATER_TANK_BYTE:
            sensors.water_tank_full = f2[F2_WATER_TANK_BYTE] == 0xFF
        if len(f2) > F2_ODOR_LEVEL_BYTE:
            sensors.odor_level = f2[F2_ODOR_LEVEL_BYTE]
        if len(f2) > F2_DUST_LEVEL_BYTE:
            sensors.dust_level = f2[F2_DUST_LEVEL_BYTE]
        if len(f2) > F2_OVERALL_DIRT_BYTE:
            sensors.overall_dirt = OVERALL_DIRT_LEVELS.get(f2[F2_OVERALL_DIRT_BYTE])
        if len(f2) > F2_LIGHT_DETECTED_BYTE:
            sensors.light_detected = f2[F2_LIGHT_DETECTED_BYTE] == 0xFF

    # Filter life percentages from F0 (limits) + F1 (usage)
    f0 = properties.get(EPC_EXTENDED_STATUS)
    if f0 and f1:
        if len(f0) > F0_DUST_FILTER_LIMIT + 1 and len(f1) > F1_DUST_FILTER_USED + 1:
            sensors.filters.hepa = _calc_filter_pct(
                _u16(f0, F0_DUST_FILTER_LIMIT), _u16(f1, F1_DUST_FILTER_USED)
            )
        if len(f0) > F0_SMELL_FILTER_LIMIT + 1 and len(f1) > F1_SMELL_FILTER_USED + 1:
            sensors.filters.deodorizing = _calc_filter_pct(
                _u16(f0, F0_SMELL_FILTER_LIMIT), _u16(f1, F1_SMELL_FILTER_USED)
            )
        if len(f0) > F0_HUMID_FILTER_LIMIT + 1 and len(f1) > F1_HUMID_FILTER_USED + 1:
            sensors.filters.humidifying = _calc_filter_pct(
                _u16(f0, F0_HUMID_FILTER_LIMIT), _u16(f1, F1_HUMID_FILTER_USED)
            )
        if len(f0) > F0_ION_UNIT_LIMIT and len(f1) > F1_ION_UNIT_USED:
            sensors.filters.ion_unit = _calc_filter_pct(
                f0[F0_ION_UNIT_LIMIT], f1[F1_ION_UNIT_USED]
            )
        if len(f0) > F0_PCI_UNIT_LIMIT + 1 and len(f1) > F1_PCI_SENSOR_B + 1:
            # Plasmacluster (PCI): usage = max of two sensor values
            pci_used = max(_u16(f1, F1_PCI_SENSOR_A), _u16(f1, F1_PCI_SENSOR_B))
            sensors.filters.plasmacluster = _calc_filter_pct(
                _u16(f0, F0_PCI_UNIT_LIMIT), pci_used
            )

    return sensors


class SharpCocoroAirApi:
    """Async client for Sharp Cocoro Air EU API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        *,
        email: str = "",
        password: str = "",
        terminal_app_id: str = "",
    ) -> None:
        self._session = session
        self._terminal_app_id = terminal_app_id
        self._authenticated = False
        self._paired_box_ids: set[str] = set()
        self._email = email
        self._password = password

    @property
    def authenticated(self) -> bool:
        return self._authenticated

    @property
    def terminal_app_id(self) -> str:
        return self._terminal_app_id

    def _hms_url(self, path: str, extra_params: dict[str, str] | None = None) -> str:
        """Build HMS API URL with appSecret."""
        params = {"appSecret": HMS_APP_SECRET}
        if extra_params:
            params.update(extra_params)
        return f"{HMS_API_BASE}{path}?{urlencode(params)}"

    def _browser_headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,*/*",
        }

    def _api_headers(self) -> dict[str, str]:
        return {
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }

    async def async_login(self, email: str, password: str) -> None:
        """Execute full OAuth authentication flow.

        Generates a new terminalAppId. After this, caller should either:
        - Call async_ensure_paired() (first-ever setup), or
        - Call async_tid_login() with old terminalAppId (dual-login pattern)

        Raises AuthenticationError on invalid credentials.
        Raises ApiConnectionError on network/server errors.
        """
        self._email = email
        self._password = password
        self._authenticated = False

        try:
            auth_code, nonce = await self._oauth_flow(email, password)
            self._terminal_app_id = await self._get_terminal_app_id()
            self._paired_box_ids = set()
            await self._hms_login(auth_code, nonce)
            await self._get_user_info()

            self._authenticated = True
            _LOGGER.debug("Full OAuth login successful (new terminalAppId)")

        except AuthenticationError:
            raise
        except aiohttp.ClientError as err:
            raise ApiConnectionError(f"Connection error: {err}") from err

    async def _oauth_flow(self, email: str, password: str) -> tuple[str, str]:
        """Execute OAuth flow: authorize → login form → extract auth code.

        Returns (auth_code, nonce).
        """
        nonce = secrets.token_hex(16)
        params = {
            "scope": "openid profile email",
            "client_id": OAUTH_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": OAUTH_REDIRECT_URI,
            "nonce": nonce,
            "ui_locales": "en",
        }
        authorize_url = f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}"

        # Step 1: Follow redirects to get login page
        login_page_url, login_html = await self._follow_to_html(authorize_url)

        # Step 2: Parse and submit login form
        auth_code = await self._submit_login_form(
            login_page_url, login_html, email, password
        )

        if not auth_code:
            raise AuthenticationError("Failed to obtain OAuth authorization code")

        return auth_code, nonce

    async def _follow_to_html(self, url: str) -> tuple[str, str]:
        """Follow redirects until we get an HTML page. Returns (final_url, html)."""
        for _ in range(10):
            async with self._session.get(
                url,
                headers=self._browser_headers(),
                allow_redirects=False,
            ) as resp:
                if resp.status >= 300 and resp.status < 400:
                    location = resp.headers.get("Location", "")
                    if location.startswith("http"):
                        url = location
                    else:
                        url = urljoin(url, location)
                    continue
                if resp.status >= 400:
                    raise ApiConnectionError(
                        f"Unexpected status {resp.status} loading login page"
                    )
                html = await resp.text()
                return url, html

        raise ApiConnectionError("Too many redirects while loading login page")

    async def _submit_login_form(
        self, page_url: str, html: str, email: str, password: str
    ) -> str | None:
        """Parse JSF login form, submit credentials, follow redirects to get auth code."""
        # Extract form action
        action_match = re.search(r'action="([^"]+)"', html)
        if not action_match:
            _LOGGER.error("No form action found in login page")
            return None

        form_action = unescape(action_match.group(1))
        post_url = form_action if form_action.startswith("http") else urljoin(page_url, form_action)

        # Extract hidden fields
        hidden_fields: dict[str, str] = {}
        for m in re.finditer(r'<input[^>]*type=["\']hidden["\'][^>]*>', html, re.IGNORECASE):
            tag = m.group(0)
            name_m = re.search(r'name=["\']([^"\']+)["\']', tag)
            value_m = re.search(r'value=["\']([^"\']*?)["\']', tag)
            if name_m:
                hidden_fields[name_m.group(1)] = value_m.group(1) if value_m else ""

        # Find username field (type=text or type=email)
        username_field = self._find_input_name(html, r'type=["\'](?:text|email)["\']')
        password_field = self._find_input_name(html, r'type=["\']password["\']')

        # Find submit button
        submit_btn = self._find_input_name(html, r'type=["\']submit["\']')

        form_data = {
            **hidden_fields,
            username_field or "loginForm:username": email,
            password_field or "loginForm:password": password,
        }
        if submit_btn:
            form_data[submit_btn] = ""
        form_data["loginForm:loginButton"] = ""

        # POST login form
        async with self._session.post(
            post_url,
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "text/html,application/xhtml+xml,*/*",
            },
            data=form_data,
            allow_redirects=False,
        ) as resp:
            location = resp.headers.get("Location")

            if not location:
                if resp.status >= 500:
                    raise ApiConnectionError(f"Server error during login: {resp.status}")
                body = await resp.text()
                error_match = re.search(
                    r'class="[^"]*error[^"]*"[^>]*>([^<]+)', body, re.IGNORECASE
                )
                if error_match:
                    _LOGGER.error("Login error: %s", error_match.group(1).strip())
                raise AuthenticationError("Login failed — invalid credentials or form structure changed")

        # Follow redirect chain until sharp-cocoroair-eu://authorize?code=...
        return await self._follow_redirects_for_code(location, post_url)

    async def _follow_redirects_for_code(
        self, location: str, base_url: str
    ) -> str | None:
        """Follow 302 redirects until we hit the OAuth callback with auth code."""
        for _ in range(10):
            if not location:
                return None

            if "sharp-cocoroair-eu://" in location:
                parsed = urlparse(location)
                params = parse_qs(parsed.query)
                code = params.get("code", [None])[0]
                _LOGGER.debug("Obtained OAuth auth code")
                return code

            url = location if location.startswith("http") else urljoin(base_url, location)

            async with self._session.get(
                url,
                headers=self._browser_headers(),
                allow_redirects=False,
            ) as resp:
                location = resp.headers.get("Location")

        _LOGGER.error("Failed to find OAuth callback in redirect chain")
        return None

    async def _get_terminal_app_id(self) -> str:
        """Get terminalAppId from HMS API."""
        url = self._hms_url("setting/terminalAppId/")

        async with self._session.get(url, headers=self._api_headers()) as resp:
            if resp.status != 200:
                raise ApiConnectionError(f"terminalAppId request failed: {resp.status}")
            data = await resp.json()
            terminal_id = data.get("terminalAppId", "")
            if not terminal_id:
                raise ApiConnectionError("Empty terminalAppId in response")
            return terminal_id

    async def _hms_login(self, auth_code: str, nonce: str) -> None:
        """Login to HMS with OAuth auth code (NOT token exchange).

        EU always requires password (nonce from OAuth authorize).
        Body: {terminalAppId, tempAccToken, password}.
        """
        url = self._hms_url(
            "setting/login/", extra_params={"serviceName": HMS_SERVICE_NAME}
        )
        payload = {
            "terminalAppId": self._terminal_app_id,
            "tempAccToken": auth_code,
            "password": nonce,
        }

        async with self._session.post(
            url, headers=self._api_headers(), json=payload
        ) as resp:
            if resp.status == 200:
                _LOGGER.debug("HMS login successful")
                return
            body = await resp.text()
            _LOGGER.error("HMS login failed: %s %s", resp.status, body[:200])

        raise AuthenticationError("HMS login failed")

    async def _get_user_info(self) -> dict:
        """Get user info to validate session."""
        url = self._hms_url(
            "setting/userInfo",
            extra_params={"terminalAppId": self._terminal_app_id},
        )

        async with self._session.get(url, headers=self._api_headers()) as resp:
            if resp.status != 200:
                raise AuthenticationError("Failed to get user info — session invalid")
            return await resp.json()

    async def async_get_devices(self) -> list[DeviceInfo]:
        """Fetch device list and parse ECHONET properties.

        Raises AuthenticationError if session expired.
        Raises ApiConnectionError on network errors.
        """
        url = self._hms_url("setting/boxInfo", extra_params={"mode": "other"})

        try:
            async with self._session.get(url, headers=self._api_headers()) as resp:
                if resp.status in (401, 403):
                    self._authenticated = False
                    raise AuthenticationError("Session expired")
                if resp.status != 200:
                    raise ApiConnectionError(f"boxInfo request failed: {resp.status}")
                raw_text = await resp.text()
                data = json.loads(raw_text)
        except aiohttp.ClientError as err:
            raise ApiConnectionError(f"Connection error: {err}") from err

        devices: list[DeviceInfo] = []

        for box in data.get("box", []):
            box_id = box.get("boxId", "")

            for echonet in box.get("echonetData", []):
                prop_hex = echonet.get("echonetProperty", "")
                properties = _parse_echonet_properties(prop_hex) if prop_hex else {}
                sensors = _extract_sensors(properties)

                label_data = echonet.get("labelData", {})
                device = DeviceInfo(
                    box_id=box_id,
                    device_id=echonet.get("deviceId", 0),
                    model=echonet.get("model", ""),
                    maker=echonet.get("maker", "Sharp"),
                    name=label_data.get("name", echonet.get("model", "Sharp Device")),
                    device_type=label_data.get("deviceType", ""),
                    echonet_node=echonet.get("echonetNode", ""),
                    echonet_object=echonet.get("echonetObject", ""),
                    sensors=sensors,
                    raw_response=raw_text,
                )
                devices.append(device)
                if box_id:
                    self._paired_box_ids.add(box_id)

        return devices

    async def async_register_terminal(self) -> None:
        """Register this client as a terminal with HMS.

        Required before pairing.
        """
        url = self._hms_url("setting/terminal")
        payload = {
            "pushId": "",
            "os": TERMINAL_OS,
            "osVersion": TERMINAL_OS_VERSION,
            "appName": TERMINAL_APP_NAME,
            "name": TERMINAL_NAME,
            "permitTidLogin": 1,
            "expireSecTidLogin": 0,
        }

        async with self._session.post(
            url, headers=self._api_headers(), json=payload
        ) as resp:
            if resp.status >= 500:
                raise ApiConnectionError(
                    f"Terminal registration server error: {resp.status}"
                )
            if resp.status not in (200, 201):
                body = await resp.text()
                _LOGGER.warning("Terminal registration returned %s: %s", resp.status, body[:200])
            else:
                _LOGGER.debug("Terminal registered successfully")

    async def async_pair_device(self, box_id: str) -> None:
        """Pair a device (boxId) with the current terminal.

        Without pairing, control/* endpoints return 400.
        boxId must NOT be URL-encoded (it's a raw URL).
        """
        url = (
            f"{HMS_API_BASE}setting/pairing/"
            f"?appSecret={HMS_APP_SECRET_ENCODED}"
            f"&boxId={box_id}&houseFlag=false"
        )

        async with self._session.post(
            url, headers=self._api_headers()
        ) as resp:
            if resp.status >= 500:
                raise ApiConnectionError(
                    f"Pairing server error: {resp.status}"
                )
            if resp.status in (200, 201):
                _LOGGER.debug("Device paired: ...%s", box_id[-20:])
            else:
                body = await resp.text()
                _LOGGER.warning("Pairing failed (%s): %s", resp.status, body[:200])

    async def async_ensure_paired(self, devices: list[DeviceInfo]) -> None:
        """Register terminal and pair all devices. Call once after login."""
        await self.async_register_terminal()
        for device in devices:
            await self.async_pair_device(device.box_id)
            self._paired_box_ids.add(device.box_id)

    async def async_send_control(
        self, device: DeviceInfo, power_code: str, f3_code: str
    ) -> None:
        """Send a control command to a device.

        On 400 (likely expired pairing), marks session as unauthenticated
        so that the next coordinator poll triggers re-authentication
        with the dual-login pattern (preserving pairing if possible).

        Always sends 4 statuses (80, f3, f1, f2) as the app does.
        boxId and terminalAppId are raw in the query string (not URL-encoded).
        """
        url = (
            f"{HMS_API_BASE}control/deviceControl"
            f"?appSecret={HMS_APP_SECRET_ENCODED}"
            f"&terminalAppId={self._terminal_app_id}"
            f"&boxId={device.box_id}"
        )
        payload = {
            "controlList": [
                {
                    "deviceId": device.device_id,
                    "echonetNode": device.echonet_node,
                    "echonetObject": device.echonet_object,
                    "status": [
                        {
                            "statusCode": "80",
                            "valueType": "valueSingle",
                            "valueSingle": {"code": power_code},
                        },
                        {
                            "statusCode": "f3",
                            "valueType": "valueBinary",
                            "valueBinary": {"code": f3_code},
                        },
                        {
                            "statusCode": "f1",
                            "valueType": "valueBinary",
                            "valueBinary": {"code": F1_ZEROS},
                        },
                        {
                            "statusCode": "f2",
                            "valueType": "valueBinary",
                            "valueBinary": {"code": F2_ZEROS},
                        },
                    ],
                }
            ]
        }

        try:
            async with self._session.post(
                url, headers=self._api_headers(), json=payload
            ) as resp:
                if resp.status == 200:
                    _LOGGER.debug("Control command sent: power=%s", power_code)
                elif resp.status in (400, 401, 403):
                    self._authenticated = False
                    body = await resp.text()
                    raise AuthenticationError(
                        f"Control failed ({resp.status}): {body[:200]}"
                    )
                else:
                    body = await resp.text()
                    raise ApiConnectionError(
                        f"Control failed ({resp.status}): {body[:200]}"
                    )
        except aiohttp.ClientError as err:
            raise ApiConnectionError(f"Control connection error: {err}") from err

    async def async_tid_login(self) -> bool:
        """Attempt lightweight re-login using stored terminalAppId.

        Mirrors mobile app re-launch behavior.
        If the server accepts, session is restored with the SAME terminalAppId,
        preserving existing device pairings.
        """
        if not self._terminal_app_id:
            return False

        url = self._hms_url(
            "setting/login/", extra_params={"serviceName": HMS_SERVICE_NAME}
        )
        payload = {"terminalAppId": self._terminal_app_id}

        try:
            async with self._session.post(
                url, headers=self._api_headers(), json=payload
            ) as resp:
                if resp.status == 200:
                    _LOGGER.debug("TID re-login successful (pairing preserved)")
                    self._authenticated = True
                    return True
                _LOGGER.debug(
                    "TID re-login rejected (%s), will do full OAuth", resp.status
                )
                return False
        except aiohttp.ClientError as err:
            raise ApiConnectionError(f"TID re-login connection error: {err}") from err

    async def async_ensure_authenticated(self) -> None:
        """Re-authenticate if session expired.

        Mirrors the mobile app's dual-login pattern:
        1. Try tid-login with stored terminalAppId (preserves pairing)
        2. If rejected: full OAuth → dual-login with OLD terminalAppId
           (activates old terminal in new session, pairing preserved)
        3. Only if old terminalAppId is truly dead: use new one + re-pair
        """
        if self._authenticated:
            return
        if not self._email or not self._password:
            return

        _LOGGER.debug("Session expired, attempting re-authentication")
        old_terminal_app_id = self._terminal_app_id
        old_paired_box_ids = set(self._paired_box_ids)

        # Step 1: Try tid-login (like app re-launch)
        if old_terminal_app_id:
            if await self.async_tid_login():
                return

        # Step 2: Full OAuth (gets new terminalAppId + new session)
        await self.async_login(self._email, self._password)

        # Step 3: Dual-login — activate OLD terminalAppId in new session
        # (like app initial login)
        if old_terminal_app_id:
            saved_new_id = self._terminal_app_id
            self._terminal_app_id = old_terminal_app_id
            if await self.async_tid_login():
                # Old terminalAppId works — pairing is preserved!
                self._paired_box_ids = old_paired_box_ids
                _LOGGER.debug(
                    "Dual-login successful — old terminalAppId restored, pairing preserved"
                )
                return
            # Old terminalAppId truly dead — fall back to new one
            self._terminal_app_id = saved_new_id

        # Step 4: Last resort — new terminalAppId, need fresh pairing
        _LOGGER.warning("Old terminalAppId expired, using new one — re-pairing required")
        await self.async_register_terminal()
        for box_id in old_paired_box_ids:
            await self.async_pair_device(box_id)
            self._paired_box_ids.add(box_id)

    @staticmethod
    def _find_input_name(html: str, type_pattern: str) -> str | None:
        """Find input field name by type pattern."""
        # Try: <input ... type="X" ... name="Y" ...>
        m = re.search(
            rf'<input[^>]*{type_pattern}[^>]*name=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if m:
            return m.group(1)
        # Try reverse order: <input ... name="Y" ... type="X" ...>
        m = re.search(
            rf'<input[^>]*name=["\']([^"\']+)["\'][^>]*{type_pattern}',
            html,
            re.IGNORECASE,
        )
        return m.group(1) if m else None
