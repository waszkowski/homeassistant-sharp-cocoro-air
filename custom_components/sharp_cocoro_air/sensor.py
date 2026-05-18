"""Sensor platform for Sharp Cocoro Air."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import DeviceSensors
from .entity import SharpCocoroAirEntity


@dataclass(frozen=True, kw_only=True)
class SharpSensorDescription(SensorEntityDescription):
    """Describes a Sharp Cocoro Air sensor."""

    value_fn: Callable[[DeviceSensors], Any]
    power_dependent: bool = True


def _bool_state(value: bool | None, true_state: str, false_state: str) -> str | None:
    if value is None:
        return None
    return true_state if value else false_state


SENSOR_DESCRIPTIONS: tuple[SharpSensorDescription, ...] = (
    SharpSensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.ENUM,
        options=["on", "off"],
        value_fn=lambda s: _bool_state(s.power_on, "on", "off"),
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="water_tank",
        translation_key="water_tank",
        device_class=SensorDeviceClass.ENUM,
        options=["full", "empty"],
        value_fn=lambda s: _bool_state(s.water_tank_full, "full", "empty"),
    ),
    SharpSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.temperature,
    ),
    SharpSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.humidity,
    ),
    SharpSensorDescription(
        key="fault",
        translation_key="fault",
        device_class=SensorDeviceClass.ENUM,
        options=["ok", "fault"],
        value_fn=lambda s: _bool_state(s.fault, "fault", "ok"),
    ),
    SharpSensorDescription(
        key="operation_mode",
        translation_key="operation_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["auto", "night", "pollen", "silent", "medium", "high", "ai_auto", "powerful"],
        value_fn=lambda s: s.operation_mode,
    ),
    SharpSensorDescription(
        key="humidification",
        translation_key="humidification",
        device_class=SensorDeviceClass.ENUM,
        options=["on", "off"],
        value_fn=lambda s: _bool_state(s.humidification_on, "on", "off"),
    ),
    SharpSensorDescription(
        key="fine_particles",
        translation_key="fine_particles",
        native_unit_of_measurement="pcs/L",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.fine_particles,
    ),
    SharpSensorDescription(
        key="air_quality",
        translation_key="air_quality",
        native_unit_of_measurement="/ 500",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.air_quality,
    ),
    SharpSensorDescription(
        key="odor_level",
        translation_key="odor_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.odor_level,
    ),
    SharpSensorDescription(
        key="dust_level",
        translation_key="dust_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.dust_level,
    ),
    SharpSensorDescription(
        key="overall_dirt",
        translation_key="overall_dirt",
        device_class=SensorDeviceClass.ENUM,
        options=["clean", "low", "slightly_high", "high", "very_high"],
        value_fn=lambda s: s.overall_dirt,
    ),
    SharpSensorDescription(
        key="light_detected",
        translation_key="light_detected",
        device_class=SensorDeviceClass.ENUM,
        options=["detected", "not_detected"],
        value_fn=lambda s: _bool_state(s.light_detected, "detected", "not_detected"),
    ),
    SharpSensorDescription(
        key="filter_hepa",
        translation_key="filter_hepa",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filters.hepa,
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="filter_deodorizing",
        translation_key="filter_deodorizing",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filters.deodorizing,
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="filter_humidifying",
        translation_key="filter_humidifying",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filters.humidifying,
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="filter_ion_unit",
        translation_key="filter_ion_unit",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filters.ion_unit,
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="filter_plasmacluster",
        translation_key="filter_plasmacluster",
        icon="mdi:air-filter",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.filters.plasmacluster,
        power_dependent=False,
    ),
    SharpSensorDescription(
        key="power_consumption",
        translation_key="power_consumption",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda s: s.power_consumption_watts,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sharp Cocoro Air sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator

    async_add_entities(
        SharpCocoroAirSensor(coordinator=coordinator, description=description, device=device)
        for device in coordinator.data
        for description in SENSOR_DESCRIPTIONS
    )


class SharpCocoroAirSensor(SharpCocoroAirEntity, SensorEntity):
    """Representation of a Sharp Cocoro Air sensor."""

    entity_description: SharpSensorDescription

    def __init__(
        self,
        coordinator,
        description: SharpSensorDescription,
        device,
    ) -> None:
        super().__init__(coordinator, device)
        self.entity_description = description
        self._attr_unique_id = f"{device.box_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        device = self.device
        if device is None:
            return None
        sensors = device.sensors
        if self.entity_description.power_dependent and not sensors.power_on:
            return None
        return self.entity_description.value_fn(sensors)
