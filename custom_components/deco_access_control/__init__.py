"""TP-Link Deco Access Control integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .client import DecoController
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, PLATFORMS
from .coordinator import DecoAccessCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    controller = DecoController(entry.data["host"], entry.data["username"], entry.data["password"])
    coordinator = DecoAccessCoordinator(hass, controller, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return ok
