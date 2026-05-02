"""Fan platform for Sharp Cocoro Air — air purifier control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import F3_MODE_PAYLOADS, F3_POWER_OFF, F3_POWER_ON
from .entity import SharpCocoroAirControllableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp Cocoro Air fan entities from a config entry."""
    data = entry.runtime_data
    async_add_entities(
        SharpCocoroAirFan(coordinator=data.coordinator, api=data.api, device=device)
        for device in data.coordinator.data
    )


class SharpCocoroAirFan(SharpCocoroAirControllableEntity, FanEntity):
    """Sharp Cocoro Air air purifier as a fan entity."""

    _attr_translation_key = "air_purifier"
    _attr_supported_features = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = list(F3_MODE_PAYLOADS.keys())

    def __init__(self, coordinator, api, device) -> None:
        super().__init__(coordinator, api, device)
        self._attr_unique_id = f"{device.box_id}_fan"

    @property
    def is_on(self) -> bool | None:
        device = self.device
        return None if device is None else device.sensors.power_on

    @property
    def preset_mode(self) -> str | None:
        device = self.device
        return None if device is None else device.sensors.operation_mode

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the air purifier on."""
        device = self.device
        if device is None:
            return
        if preset_mode and preset_mode in F3_MODE_PAYLOADS:
            await self._send_control(device, "30", F3_MODE_PAYLOADS[preset_mode])
        else:
            await self._send_control(device, "30", F3_POWER_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the air purifier off."""
        device = self.device
        if device is None:
            return
        await self._send_control(device, "31", F3_POWER_OFF)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set operation mode (also turns device on)."""
        device = self.device
        if device is None:
            return
        f3_payload = F3_MODE_PAYLOADS.get(preset_mode)
        if f3_payload is None:
            return
        await self._send_control(device, "30", f3_payload)
