"""Sharp Cocoro Air integration for Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .api import SharpCocoroAirApi
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TERMINAL_APP_ID,
    DEFAULT_SCAN_INTERVAL,
    PLATFORMS,
)
from .coordinator import SharpCocoroAirCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class SharpCocoroAirData:
    """Runtime data per config entry."""

    coordinator: SharpCocoroAirCoordinator
    api: SharpCocoroAirApi
    session: aiohttp.ClientSession


type SharpCocoroAirConfigEntry = ConfigEntry[SharpCocoroAirData]


async def async_setup_entry(hass: HomeAssistant, entry: SharpCocoroAirConfigEntry) -> bool:
    """Set up Sharp Cocoro Air from a config entry."""
    # Custom cookie jar required for multi-step OAuth auth flow
    cookie_jar = aiohttp.CookieJar(unsafe=True)
    session = aiohttp.ClientSession(cookie_jar=cookie_jar)

    cached_terminal_id = entry.data.get(CONF_TERMINAL_APP_ID, "")
    api = SharpCocoroAirApi(
        session,
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        terminal_app_id=cached_terminal_id,
    )

    try:
        # If we have a cached terminal_app_id, ensure_authenticated tries
        # tid-login first (preserves Sharp account terminal slot).
        # Otherwise it falls back to full OAuth + register + pair below.
        await api.async_ensure_authenticated()

        devices = await api.async_get_devices()
        if not cached_terminal_id:
            # First-ever setup — explicit register + pair required
            await api.async_ensure_paired(devices)

        scan_minutes = entry.options.get(
            CONF_SCAN_INTERVAL,
            int(DEFAULT_SCAN_INTERVAL.total_seconds() / 60),
        )
        update_interval = timedelta(minutes=scan_minutes)

        coordinator = SharpCocoroAirCoordinator(hass, api, update_interval)
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await session.close()
        raise

    # Persist terminal_app_id (first time, or after rotation by ensure_authenticated)
    if api.terminal_app_id != cached_terminal_id:
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, CONF_TERMINAL_APP_ID: api.terminal_app_id},
        )

    entry.runtime_data = SharpCocoroAirData(
        coordinator=coordinator, api=api, session=session
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SharpCocoroAirConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.session.close()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: SharpCocoroAirConfigEntry
) -> None:
    """Handle options update — reload integration."""
    await hass.config_entries.async_reload(entry.entry_id)
