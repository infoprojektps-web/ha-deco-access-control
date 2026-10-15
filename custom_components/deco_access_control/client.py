"""Fail-closed Deco API wrapper. Never replace the whole blocked-MAC list."""
from dataclasses import dataclass
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
class Snapshot:
    clients: dict[str, ClientInfo]
    blocked: frozenset[str]

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
        return parse_snapshot(api.get_client_list(), api.clients.get_blocked())

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
