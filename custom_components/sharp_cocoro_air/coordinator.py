"""Data update coordinator for Sharp Cocoro Air."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiConnectionError, AuthenticationError, DeviceInfo, SharpCocoroAirApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SharpCocoroAirCoordinator(DataUpdateCoordinator[list[DeviceInfo]]):
    """Coordinator to poll Sharp Cocoro Air API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: SharpCocoroAirApi,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.api = api
        self._delayed_refresh_unsub: CALLBACK_TYPE | None = None

    def async_request_delayed_refresh(self, delay: float = 5.0) -> None:
        """Schedule a coordinator refresh after a delay.

        Used after control commands — the device needs time to report
        its new state to the Sharp cloud before we poll.
        """
        if self._delayed_refresh_unsub:
            self._delayed_refresh_unsub()

        async def _do_refresh(_now: object) -> None:
            self._delayed_refresh_unsub = None
            await self.async_request_refresh()

        self._delayed_refresh_unsub = async_call_later(
            self.hass, delay, _do_refresh
        )

    async def _async_update_data(self) -> list[DeviceInfo]:
        """Fetch device data from API."""
        try:
            return await self._fetch_with_reauth()
        except AuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ApiConnectionError as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_with_reauth(self) -> list[DeviceInfo]:
        """Fetch devices, retrying once after re-auth on server-side expiry."""
        await self.api.async_ensure_authenticated()
        try:
            return await self.api.async_get_devices()
        except AuthenticationError:
            # async_get_devices cleared _authenticated → ensure_auth re-runs
            # tid-login → OAuth → dual-login flow
            _LOGGER.debug("Session expired server-side, attempting re-auth")
            await self.api.async_ensure_authenticated()
            return await self.api.async_get_devices()
