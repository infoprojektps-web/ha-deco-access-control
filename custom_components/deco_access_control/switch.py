"""Per-client switch. ON=Wi-Fi allowed; OFF=blocked."""
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import DecoAccessCoordinator

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: DecoAccessCoordinator = hass.data[DOMAIN][entry.entry_id]
    registered = set()

    def add_new_clients():
        if coordinator.data is None:
            return
        unseen = set(coordinator.data.clients) - registered
        if unseen:
            registered.update(unseen)
            async_add_entities(
                [DecoClientAccessSwitch(coordinator, entry.entry_id, mac) for mac in sorted(unseen)]
            )

    entry.async_on_unload(coordinator.async_add_listener(add_new_clients))
    add_new_clients()

class DecoClientAccessSwitch(CoordinatorEntity[DecoAccessCoordinator], SwitchEntity):
    _attr_icon = "mdi:wifi"
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False
    _attr_should_poll = False

    def __init__(self, coordinator, entry_id, mac):
        super().__init__(coordinator)
        self._mac = mac
        self._attr_unique_id = f"{entry_id}_{mac.replace(':', '').lower()}_access"

    @property
    def name(self):
        info = self.coordinator.data.clients.get(self._mac) if self.coordinator.data else None
        return f"Dostęp Wi-Fi — {info.name if info else self._mac}"

    @property
    def is_on(self):
        if self.coordinator.data is None:
            return None
        return self._mac not in self.coordinator.data.blocked

    @property
    def available(self):
        return (self.coordinator.last_update_success and self.coordinator.data is not None
                and self._mac in self.coordinator.data.clients)

    @property
    def extra_state_attributes(self):
        info = self.coordinator.data.clients.get(self._mac) if self.coordinator.data else None
        return {
            "mac": self._mac,
            "ip": info.ip if info else None,
            "online": info.online if info else None,
            "connection_type": info.connection_type if info else None,
            "blocked": self._mac in self.coordinator.data.blocked if self.coordinator.data else None,
        }

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_set_allowed(self._mac, True)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_set_allowed(self._mac, False)
