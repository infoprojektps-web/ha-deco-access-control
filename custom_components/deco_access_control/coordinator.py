"""Coordinator with serialized reads/writes and fail-closed errors."""
import asyncio
from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import HomeAssistantError
from .client import DecoController, Snapshot
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class DecoAccessCoordinator(DataUpdateCoordinator[Snapshot]):
    def __init__(self, hass, controller: DecoController, interval: int) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=timedelta(seconds=interval))
        self.controller = controller
        self._operation_lock = asyncio.Lock()

    async def _async_update_data(self) -> Snapshot:
        async with self._operation_lock:
            try:
                return await self.hass.async_add_executor_job(self.controller.poll)
            except Exception as err:
                raise UpdateFailed(f"Deco refresh failed ({type(err).__name__})") from err

    async def async_set_allowed(self, mac: str, allowed: bool) -> None:
        async with self._operation_lock:
            try:
                verified = await self.hass.async_add_executor_job(self.controller.set_allowed, mac, allowed)
            except Exception as err:
                self.async_update_listeners()
                raise HomeAssistantError(
                    f"Deco access change failed ({type(err).__name__}); verify in Deco app"
                ) from err
            self.async_set_updated_data(verified)
