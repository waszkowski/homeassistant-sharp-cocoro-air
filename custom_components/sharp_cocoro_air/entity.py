"""Base entities for Sharp Cocoro Air."""

from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AuthenticationError, DeviceInfo, SharpCocoroAirApi
from .const import DOMAIN
from .coordinator import SharpCocoroAirCoordinator


class SharpCocoroAirEntity(CoordinatorEntity[SharpCocoroAirCoordinator]):
    """Base entity bound to a single Sharp device by box_id."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SharpCocoroAirCoordinator,
        device: DeviceInfo,
    ) -> None:
        super().__init__(coordinator)
        self._box_id = device.box_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.box_id)},
            "name": device.name or device.model,
            "manufacturer": device.maker or "Sharp",
            "model": device.model,
        }

    @property
    def device(self) -> DeviceInfo | None:
        """Return the current device data from the coordinator."""
        if not self.coordinator.data:
            return None
        return next(
            (d for d in self.coordinator.data if d.box_id == self._box_id),
            None,
        )


class SharpCocoroAirControllableEntity(SharpCocoroAirEntity):
    """Entity that can send control commands with auto re-auth + delayed refresh."""

    def __init__(
        self,
        coordinator: SharpCocoroAirCoordinator,
        api: SharpCocoroAirApi,
        device: DeviceInfo,
    ) -> None:
        super().__init__(coordinator, device)
        self._api = api

    async def _send_control(
        self, device: DeviceInfo, power_code: str, f3_code: str
    ) -> None:
        """Send control, retrying once after re-auth on session expiry."""
        try:
            await self._api.async_send_control(device, power_code, f3_code)
        except AuthenticationError:
            await self._api.async_ensure_authenticated()
            await self._api.async_send_control(device, power_code, f3_code)
        self.coordinator.async_request_delayed_refresh()
