"""Fail-closed Deco API wrapper. Never replace the whole blocked-MAC list."""
from dataclasses import dataclass, replace
from threading import RLock
from typing import Callable
import re
import hashlib
import json

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
    error_code: int | None = None
    signature: str | None = None
    count: int | None = None


@dataclass(frozen=True)
class Snapshot:
    clients: dict[str, ClientInfo]
    blocked: frozenset[str]
    wifi_access: WifiAccessProbe | None = None
    nrd_blacklist: WifiAccessProbe | None = None
    wifi_refused: WifiAccessProbe | None = None
    firmware_client_blocked: dict[str, str] | None = None
    blacklist_entry_signatures: dict[str, str] | None = None
    blacklist_entry_fields: dict[str, tuple[str, ...]] | None = None

def _api_error_code(exc: Exception) -> int | None:
    """Expose only numeric Deco error_code, never raw exception text."""
    value = getattr(exc, "error_code", None)
    return value if type(value) is int else None


def _read_only_probe(api, path: str, form: str, operation: str) -> tuple[WifiAccessProbe, dict | None]:
    """Safely inspect a supported read-only endpoint.

    No raw response data, MAC addresses, tokens, credentials, or router URLs
    are surfaced via entity attributes or error messages.
    """
    try:
        result = api.request(path, form, {"operation": operation})
    except Exception as exc:
        code = _api_error_code(exc)
        return (WifiAccessProbe(
            status="api_error" if code is not None else "request_error",
            error_type=type(exc).__name__,
            error_code=code,
        ), None)
    if not isinstance(result, dict):
        return WifiAccessProbe(status="unexpected_response"), None
    signature = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()[:16]
    return WifiAccessProbe(
        status="ok",
        keys=tuple(sorted(str(key) for key in result)),
        signature=signature,
    ), result


def read_wifi_access_probe(api) -> WifiAccessProbe:
    """Inspect app-only Wi-Fi access control; may be rejected by firmware."""
    base, result = _read_only_probe(api, "admin/client", "apply_list", "get")
    if result is None:
        return base
    mode = result.get("curr_mode")
    if mode is None and isinstance(result.get("apply_list"), dict):
        mode = result["apply_list"].get("curr_mode")
    return replace(base, mode=str(mode) if mode is not None else None)


def read_nrd_blacklist_probe(api) -> WifiAccessProbe:
    """Inspect the separate NRD blacklist; never make writes here."""
    base, result = _read_only_probe(api, "admin/nrd", "black_list", "list")
    if result is None:
        return base
    items = result.get("client_list")
    if isinstance(items, list):
        return replace(base, count=len(items))
    if items == {}:
        return replace(base, count=0)
    return replace(base, status="unexpected_response")


def read_wifi_refused_probe(api) -> WifiAccessProbe:
    """Inspect app-side Wi-Fi refused clients without exposing client records."""
    base, _result = _read_only_probe(api, "admin/client", "access_refuse", "get")
    return base

def read_firmware_client_blocked(api) -> dict[str, str] | None:
    """Inspect firmware-provided `client_list[].blocked` without changing it.

    It is independent of the black_list membership. Unknown/missing values are
    kept distinguishable from explicit false; failures never interrupt polling.
    """
    try:
        result = api.request(
            "admin/client", "client_list",
            {"operation": "read", "params": {"device_mac": "default"}},
        )
    except Exception:
        return None
    if not isinstance(result, dict) or not isinstance(result.get("client_list"), list):
        return None
    flags: dict[str, str] = {}
    for item in result["client_list"]:
        if not isinstance(item, dict):
            continue
        try:
            mac = normalize_mac(item.get("mac"))
        except DecoAccessError:
            continue
        value = item.get("blocked")
        if value is True or (type(value) is int and value == 1) or value == "1":
            flags[mac] = "true"
        elif value is False or (type(value) is int and value == 0) or value == "0":
            flags[mac] = "false"
        else:
            flags[mac] = "unknown"
    return flags


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
    def _snapshot(api, with_diagnostics: bool = False) -> Snapshot:
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
        # Observe exact *record shape* created by app vs Home Assistant.
        # The digest intentionally excludes the MAC address and never
        # exposes raw values, names or addresses in Home Assistant.
        signatures: dict[str, str] = {}
        fields: dict[str, tuple[str, ...]] = {}
        if isinstance(raw_entries, list):
            for raw in raw_entries:
                try:
                    mac = normalize_mac(raw.get("mac"))
                except DecoAccessError:
                    continue
                if not all(isinstance(key, str) for key in raw):
                    continue
                canonical = {key: value for key, value in raw.items() if key != "mac"}
                signature = hashlib.sha256(
                    json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str)
                    .encode("utf-8")
                ).hexdigest()[:16]
                signatures[mac] = signature
                fields[mac] = tuple(sorted(canonical))
        base = replace(
            base,
            blacklist_entry_signatures=signatures,
            blacklist_entry_fields=fields,
        )
        if with_diagnostics:
            return replace(
                base,
                wifi_access=read_wifi_access_probe(api),
                nrd_blacklist=read_nrd_blacklist_probe(api),
                wifi_refused=read_wifi_refused_probe(api),
                firmware_client_blocked=read_firmware_client_blocked(api),
            )
        return base

    def poll(self) -> Snapshot:
        with self._lock, self._factory(self._host, self._username, self._password) as api:
            return self._snapshot(api, with_diagnostics=True)

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
