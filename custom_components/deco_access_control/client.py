"""Fail-closed Deco API wrapper. Never replace the whole blocked-MAC list."""
from dataclasses import dataclass, replace
from threading import RLock
from typing import Callable
import re

MAC_PATTERN = re.compile(r"^[0-9A-F]{2}(:[0-9A-F]{2}){5}$")

class DecoAccessError(Exception):
    """Deco API unavailable or returned invalid data."""

class DecoWriteNotConfirmed(DecoAccessError):
    """Requested change was not confirmed by readback."""

def normalize_mac(value: object) -> str:
    if not isinstance(value, str):
        raise DecoAccessError("Missing or malformed client MAC")
    mac = value.strip().upper().replace("-", ":")
    if not MAC_PATTERN.fullmatch(mac):
        raise DecoAccessError("Invalid client MAC")
    return mac

@dataclass(frozen=True)
class ClientInfo:
    mac: str
    name: str
    client_type: object
    ip: str | None
    connection_type: str | None
    online: bool

@dataclass(frozen=True)
class WifiAccessProbe:
    """Read-only inspection of the Wi-Fi Access Control configuration."""
    status: str
    mode: str | None = None
    keys: tuple[str, ...] = ()
    error_type: str | None = None


@dataclass(frozen=True)
class Snapshot:
    clients: dict[str, ClientInfo]
    blocked: frozenset[str]
    wifi_access: WifiAccessProbe | None = None

def read_wifi_access_probe(api) -> WifiAccessProbe:
    """Query app-side Wi-Fi access control without modifying router settings.

    Router firmware differs; errors and missing forms are reported but do not
    prevent the base client/blocklist integration from working.
    Never expose raw response values such as client MACs or tokens.
    """
    try:
        result = api.request("admin/client", "apply_list", {"operation": "get"})
    except Exception as exc:
        return WifiAccessProbe(status="unavailable", error_type=type(exc).__name__)
    if not isinstance(result, dict):
        return WifiAccessProbe(status="unexpected_response")
    mode = result.get("curr_mode")
    if mode is None and isinstance(result.get("apply_list"), dict):
        mode = result["apply_list"].get("curr_mode")
    if mode is not None and not isinstance(mode, str):
        mode = str(mode)
    return WifiAccessProbe(
        status="available",
        mode=mode,
        keys=tuple(sorted(str(key) for key in result)),
    )

def parse_snapshot(active: object, blocked: object) -> Snapshot:
    if not isinstance(active, (list, tuple)) or not isinstance(blocked, (list, tuple)):
        raise DecoAccessError("Invalid client/blocklist response")
    clients = {}
    for obj in active:
        mac = normalize_mac(getattr(obj, "mac", None))
        clients[mac] = ClientInfo(
            mac, str(getattr(obj, "name", "") or mac),
            getattr(obj, "client_type", None) or getattr(obj, "device_type", None) or "other",
            str(getattr(obj, "ip", "") or "") or None,
            str(getattr(obj, "connection_type", "") or "") or None,
            bool(getattr(obj, "online", True)),
        )
    blocked_macs = set()
    for obj in blocked:
        mac = normalize_mac(getattr(obj, "mac", None))
        blocked_macs.add(mac)
        clients.setdefault(mac, ClientInfo(mac, str(getattr(obj, "name", "") or mac),
                                           getattr(obj, "client_type", None) or "other", None, None, False))
    return Snapshot(clients, frozenset(blocked_macs))

def _default_client_factory(host, username, password):
    from tplink_deco_api import DecoClient
    return DecoClient(host, username, password)

class DecoController:
    def __init__(self, host: str, username: str, password: str,
                 factory: Callable = _default_client_factory):
        self._host, self._username, self._password = host, username, password
        self._factory = factory
        self._lock = RLock()

    @staticmethod
    def _snapshot(api) -> Snapshot:
        # The upstream SDK treats missing/malformed blocked-client lists
        # as empty. Validate the raw response BEFORE trusting that fallback.
        raw_result = api.request("admin/client", "black_list", {"operation": "list"})
        if not isinstance(raw_result, dict) or "client_list" not in raw_result:
            raise DecoAccessError("Incomplete Deco blocklist response; no change allowed")
        raw_entries = raw_result["client_list"]
        if not (isinstance(raw_entries, list) or raw_entries == {}):
            raise DecoAccessError("Malformed Deco blocklist response; no change allowed")
        if isinstance(raw_entries, list) and not all(isinstance(x, dict) for x in raw_entries):
            raise DecoAccessError("Malformed Deco blocklist entry; no change allowed")
        base = parse_snapshot(api.get_client_list(), api.clients.get_blocked())
        return replace(base, wifi_access=read_wifi_access_probe(api))

    def poll(self) -> Snapshot:
        with self._lock, self._factory(self._host, self._username, self._password) as api:
            return self._snapshot(api)

    def set_allowed(self, mac: str, allowed: bool) -> Snapshot:
        target = normalize_mac(mac)
        with self._lock, self._factory(self._host, self._username, self._password) as api:
            before = self._snapshot(api)
            if target not in before.clients:
                raise DecoAccessError("Client not found; no change made")
            if (target not in before.blocked) != allowed:
                if allowed:
                    api.clients.unblock(target)
                else:
                    info = before.clients[target]
                    api.clients.block(target, info.name, info.client_type)
            after = self._snapshot(api)
            if (target not in after.blocked) != allowed:
                raise DecoWriteNotConfirmed("Access change not confirmed")
            return after
