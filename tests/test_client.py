"""Offline mock tests. No router or HA dependency."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "custom_components" / "deco_access_control"))
from client import DecoController, DecoAccessError, DecoWriteNotConfirmed, normalize_mac

MAC_A = "AA:BB:CC:DD:EE:01"
MAC_B = "AA:BB:CC:DD:EE:02"

class FakeDeco:
    def __init__(self, blocked=None, clients=None):
        self._blocked = set(blocked or ())
        self._clients = list(clients) if clients is not None else [
            SimpleNamespace(mac=MAC_A, name="Phone A", ip="192.168.0.30", client_type="phone", online=True, connection_type="band5"),
            SimpleNamespace(mac=MAC_B, name="Phone B", ip="192.168.0.31", client_type="phone", online=True, connection_type="band5"),
        ]
        self.fail_read = False
        self.ignore_write = False
        self.operations = []
        self.clients = self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def get_client_list(self):
        return self._clients
    def get_blocked(self):
        if self.fail_read:
            raise ConnectionError("unavailable")
        return [SimpleNamespace(mac=m, name=f"Blocked {m}", client_type="phone") for m in self._blocked]
    def block(self, mac, name, client_type):
        self.operations.append(("block", mac, name, client_type))
        if not self.ignore_write:
            self._blocked.add(mac)
    def unblock(self, mac):
        self.operations.append(("unblock", mac))
        if not self.ignore_write:
            self._blocked.discard(mac)

class ClientTests(unittest.TestCase):
    def controller(self, fake):
        return DecoController("192.168.0.205", "admin", "dummy", factory=lambda *_: fake)
    def test_mac_normalization(self):
        self.assertEqual(normalize_mac("aa-bb-cc-dd-ee-01"), MAC_A)
        with self.assertRaises(DecoAccessError):
            normalize_mac("bad")
    def test_poll_all_clients(self):
        result = self.controller(FakeDeco(blocked={MAC_B})).poll()
        self.assertEqual(set(result.clients), {MAC_A, MAC_B})
        self.assertEqual(result.blocked, frozenset({MAC_B}))
    def test_fail_closed_read_error_does_not_write(self):
        fake = FakeDeco(blocked={MAC_B})
        fake.fail_read = True
        with self.assertRaises(ConnectionError):
            self.controller(fake).set_allowed(MAC_A, False)
        self.assertEqual(fake.operations, [])
        self.assertEqual(fake._blocked, {MAC_B})
    def test_targeted_block_preserves_other_entries(self):
        fake = FakeDeco(blocked={MAC_B})
        result = self.controller(fake).set_allowed(MAC_A, False)
        self.assertEqual(fake._blocked, {MAC_A, MAC_B})
        self.assertEqual(len(fake.operations), 1)
        self.assertEqual(result.blocked, frozenset({MAC_A, MAC_B}))
    def test_targeted_unblock_preserves_other_entries(self):
        fake = FakeDeco(blocked={MAC_A, MAC_B})
        self.controller(fake).set_allowed(MAC_A, True)
        self.assertEqual(fake._blocked, {MAC_B})
    def test_noop_does_not_write(self):
        fake = FakeDeco(blocked={MAC_A})
        self.controller(fake).set_allowed(MAC_A, False)
        self.assertEqual(fake.operations, [])
    def test_unconfirmed_write_is_error(self):
        fake = FakeDeco()
        fake.ignore_write = True
        with self.assertRaises(DecoWriteNotConfirmed):
            self.controller(fake).set_allowed(MAC_A, False)
    def test_missing_target_is_error(self):
        fake = FakeDeco()
        with self.assertRaises(DecoAccessError):
            self.controller(fake).set_allowed("AA:BB:CC:DD:EE:99", False)
        self.assertFalse(fake.operations)
    def test_malformed_read_blocks_write(self):
        fake = FakeDeco(clients=[SimpleNamespace(mac="invalid")])
        with self.assertRaises(DecoAccessError):
            self.controller(fake).set_allowed(MAC_A, False)
        self.assertFalse(fake.operations)

if __name__ == "__main__":
    unittest.main()
