"""Read-only Wi-Fi Access Control diagnostics (no changes sent to Deco)."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import DecoAccessCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: DecoAccessCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DecoWifiAccessDiagnostic(coordinator, entry.entry_id),
        DecoBlacklistCount(coordinator, entry.entry_id),
        DecoReadOnlyProbe(coordinator, entry.entry_id, "nrd_blacklist", "Deco — diagnostyka NRD black_list"),
        DecoReadOnlyProbe(coordinator, entry.entry_id, "wifi_refused", "Deco — diagnostyka Wi-Fi access_refuse"),
    ])


class DecoWifiAccessDiagnostic(CoordinatorEntity[DecoAccessCoordinator], SensorEntity):
    """Show state of app-specific Wi-Fi Access Control mode, if supported."""

    _attr_name = "Deco — diagnostyka kontroli Wi-Fi"
    _attr_icon = "mdi:shield-search"
    _attr_has_entity_name = False

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_wifi_access_diagnostic"

    @property
    def native_value(self):
        snapshot = self.coordinator.data
        if snapshot is None or snapshot.wifi_access is None:
            return "brak danych"
        probe = snapshot.wifi_access
        if probe.status != "ok":
            return "błąd API" if probe.status == "api_error" else probe.status
        return probe.mode or "nieznany tryb"

    @property
    def extra_state_attributes(self):
        snapshot = self.coordinator.data
        probe = snapshot.wifi_access if snapshot else None
        if probe is None:
            return {}
        return {
            "endpoint_status": probe.status,
            "active_mode": probe.mode,
            "response_fields": ", ".join(probe.keys),
            "error_type": probe.error_type,
            "error_code": probe.error_code,
            "configuration_signature": probe.signature,
            "note": "Odczyt tylko diagnostyczny. Wpis na black_list nie potwierdza odciecia internetu.",
        }


class DecoBlacklistCount(CoordinatorEntity[DecoAccessCoordinator], SensorEntity):
    """Number of entries on /admin/client black_list, not an enforcement metric."""

    _attr_name = "Deco — liczba wpisów na black_list"
    _attr_icon = "mdi:account-cancel-outline"
    _attr_has_entity_name = False
    _attr_native_unit_of_measurement = "urządzeń"

    def __init__(self, coordinator, entry_id):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_blacklist_count"

    @property
    def native_value(self):
        return len(self.coordinator.data.blocked) if self.coordinator.data is not None else None

class DecoReadOnlyProbe(CoordinatorEntity[DecoAccessCoordinator], SensorEntity):
    """Sanitized read-only status from another Deco endpoint."""

    _attr_icon = "mdi:shield-search"
    _attr_has_entity_name = False

    def __init__(self, coordinator, entry_id, probe_key, title):
        super().__init__(coordinator)
        self._key = probe_key
        self._attr_name = title
        self._attr_unique_id = f"{entry_id}_{probe_key}_diagnostic"

    @property
    def _probe(self):
        data = self.coordinator.data
        return getattr(data, self._key, None) if data else None

    @property
    def native_value(self):
        probe = self._probe
        if probe is None:
            return "brak danych"
        if probe.status == "api_error":
            return "błąd API"
        if probe.status != "ok":
            return probe.status
        if probe.count is not None:
            return f"{probe.count} wpisów"
        return "odczyt OK"

    @property
    def extra_state_attributes(self):
        probe = self._probe
        if probe is None:
            return {}
        return {
            "endpoint_status": probe.status,
            "error_type": probe.error_type,
            "error_code": probe.error_code,
            "response_fields": ", ".join(probe.keys),
            "entry_count": probe.count,
            "configuration_signature": probe.signature,
        }
