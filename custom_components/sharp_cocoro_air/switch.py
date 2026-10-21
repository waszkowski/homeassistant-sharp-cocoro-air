"""Switch platform for Sharp Cocoro Air — humidification and child lock control."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import F2_CHILD_LOCK_OFF, F2_CHILD_LOCK_ON, F3_CHILD_LOCK_OFF, F3_CHILD_LOCK_ON, F3_HUMID_OFF, F3_HUMID_ON
from .entity import SharpCocoroAirControllableEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp Cocoro Air switch entities from a config entry."""
    data = entry.runtime_data
    entities: list[SwitchEntity] = []
    for device in data.coordinator.data:
        entities.append(
            SharpCocoroAirHumidificationSwitch(
                coordinator=data.coordinator, api=data.api, device=device
            )
        )
        entities.append(
            SharpCocoroAirChildLockSwitch(
                coordinator=data.coordinator, api=data.api, device=device
            )
        )
    async_add_entities(entities)


class SharpCocoroAirHumidificationSwitch(SharpCocoroAirControllableEntity, SwitchEntity):
    """Switch entity for humidification control."""

    _attr_translation_key = "humidification"

    def __init__(self, coordinator, api, device) -> None:
        super().__init__(coordinator, api, device)
        self._attr_unique_id = f"{device.box_id}_humidification"

    @property
    def is_on(self) -> bool | None:
        device = self.device
        return None if device is None else device.sensors.humidification_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn humidification on (also ensures device is powered on)."""
        device = self.device
        if device is None:
            return
        await self._send_control(device, "30", F3_HUMID_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn humidification off (keeps device powered on)."""
        device = self.device
        if device is None:
            return
        await self._send_control(device, "30", F3_HUMID_OFF)


class SharpCocoroAirChildLockSwitch(SharpCocoroAirControllableEntity, SwitchEntity):
    """Switch entity for child lock control."""

    _attr_translation_key = "child_lock"

    def __init__(self, coordinator, api, device) -> None:
        super().__init__(coordinator, api, device)
        self._attr_unique_id = f"{device.box_id}_child_lock"

    @property
    def is_on(self) -> bool | None:
        device = self.device
        return None if device is None else device.sensors.child_lock

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn child lock on."""
        device = self.device
        if device is None:
            return
        power_code = "31" if device.sensors.power_on is False else "30"
        await self._send_control(device, power_code, F3_CHILD_LOCK_ON, F2_CHILD_LOCK_ON)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn child lock off."""
        device = self.device
        if device is None:
            return
        power_code = "31" if device.sensors.power_on is False else "30"
        await self._send_control(device, power_code, F3_CHILD_LOCK_OFF, F2_CHILD_LOCK_OFF)
