"""Select platform for Sharp Cocoro Air — LED brightness control."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import F3_LED_PAYLOADS
from .entity import SharpCocoroAirControllableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp Cocoro Air select entities from a config entry."""
    data = entry.runtime_data
    async_add_entities(
        SharpCocoroAirLedBrightnessSelect(
            coordinator=data.coordinator, api=data.api, device=device
        )
        for device in data.coordinator.data
    )


class SharpCocoroAirLedBrightnessSelect(SharpCocoroAirControllableEntity, SelectEntity):
    """Select entity for LED brightness control."""

    _attr_translation_key = "led_brightness"
    _attr_options = list(F3_LED_PAYLOADS.keys())

    def __init__(self, coordinator, api, device) -> None:
        super().__init__(coordinator, api, device)
        self._attr_unique_id = f"{device.box_id}_led_brightness"

    @property
    def current_option(self) -> str | None:
        device = self.device
        return None if device is None else device.sensors.led_brightness

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        device = self.device
        if device is None or option not in F3_LED_PAYLOADS:
            return
        power_code = "31" if device.sensors.power_on is False else "30"
        await self._send_control(device, power_code, F3_LED_PAYLOADS[option])

