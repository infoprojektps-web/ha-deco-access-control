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
        self.malformed_blocklist = False
        self.wifi_mode = "block"
        self.raw_record_extra = {}
        self.mobile_blocked = set()
        self.mobile_read_failure = False
        self.raw_firmware_flags = {MAC_A: True, MAC_B: False}
        self.fail_firmware_read = False
        self.ignore_write = False
        self.operations = []
        self.clients = self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def request(self, path, form, data):
        if path == "admin/mobile_app/client" and form == "black_list":
            if self.mobile_read_failure:
                raise ConnectionError("endpoint unsupported")
            return {"client_list": [
                {"mac": mac, "name": "", "client_type": "phone"}
                for mac in sorted(self.mobile_blocked)
            ]}
        if path != "admin/client":
            raise ValueError("unexpected path")
        if form == "black_list":
            if self.fail_read:
                raise ConnectionError("unavailable")
            if self.malformed_blocklist:
                return {"invalid": []}
            return {"client_list": [{"mac": mac, "name": "", "client_type": "phone", **self.raw_record_extra} for mac in self._blocked]}
        if form == "client_list":
            if self.fail_firmware_read:
                raise ConnectionError("no response")
            return {"client_list": [
                {"mac": mac.replace(":", "-"), "blocked": value}
                for mac, value in self.raw_firmware_flags.items()
            ]}
        if form == "apply_list":
            return {"curr_mode": self.wifi_mode, "clients": []}
        raise ValueError("unexpected form")
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
    def test_readonly_wifi_mode_probe(self):
        fake = FakeDeco()
        status = self.controller(fake).poll().wifi_access
        self.assertEqual(status.status, "ok")
        self.assertEqual(status.mode, "block")
        self.assertEqual(fake.operations, [])

    def test_unsupported_probes_do_not_disable_base_poll(self):
        fake = FakeDeco()
        result = self.controller(fake).poll()
        self.assertEqual(result.nrd_blacklist.status, "request_error")
        self.assertEqual(result.wifi_refused.status, "request_error")
        self.assertEqual(len(result.clients), 2)

    def test_api_error_is_reported_without_reserved_unavailable_state(self):
        from client import read_wifi_access_probe
        class ApiFailure:
            def request(self, *args):
                class FakeApiError(Exception):
                    error_code = 1234
                raise FakeApiError("secret token or MAC")
        probe = read_wifi_access_probe(ApiFailure())
        self.assertEqual(probe.status, "api_error")
        self.assertEqual(probe.error_code, 1234)
        self.assertNotIn("secret", str(probe))

    def test_firmware_blocked_flag_is_independent_from_blacklist(self):
        fake = FakeDeco(blocked={MAC_B})
        flags = self.controller(fake).poll().firmware_client_blocked
        self.assertEqual(flags[MAC_A], "true")
        self.assertEqual(flags[MAC_B], "false")
        self.assertEqual(fake.operations, [])

    def test_firmware_flag_read_error_does_not_disable_base_poll(self):
        fake = FakeDeco(blocked={MAC_B})
        fake.fail_firmware_read = True
        result = self.controller(fake).poll()
        self.assertIsNone(result.firmware_client_blocked)
        self.assertEqual(result.blocked, frozenset({MAC_B}))
        self.assertEqual(fake.operations, [])

    def test_fingerprints_do_not_expose_identity(self):
        fake = FakeDeco(blocked={MAC_B})
        snapshot = self.controller(fake).poll()
        signature = snapshot.blacklist_entry_signatures[MAC_B]
        self.assertEqual(len(signature), 16)
        self.assertNotIn(MAC_B, signature)
        self.assertEqual(snapshot.blacklist_entry_fields[MAC_B], ("client_type", "name"))
        self.assertEqual(fake.operations, [])

    def test_blocklist_entry_record_difference_detected(self):
        fake = FakeDeco(blocked={MAC_B})
        first = self.controller(fake).poll().blacklist_entry_signatures[MAC_B]
        fake.raw_record_extra = {"applied": True}
        second = self.controller(fake).poll()
        self.assertNotEqual(first, second.blacklist_entry_signatures[MAC_B])
        self.assertEqual(second.blacklist_entry_fields[MAC_B],
                         ("applied", "client_type", "name"))
        self.assertEqual(fake.operations, [])

    def test_mobile_app_blacklist_read_is_independent(self):
        fake = FakeDeco(blocked={MAC_A})
        fake.mobile_blocked = {MAC_B}
        result = self.controller(fake).poll()
        self.assertEqual(result.blocked, frozenset({MAC_A}))
        self.assertEqual(result.mobile_blacklist_macs, frozenset({MAC_B}))
        self.assertEqual(result.mobile_blacklist.status, "ok")
        self.assertEqual(result.mobile_blacklist.count, 1)
        self.assertEqual(fake.operations, [])

    def test_mobile_app_transport_status_sanitized(self):
        fake = FakeDeco()
        def request(path, form, data):
            if path == "admin/mobile_app/client":
                class SimulatedTransportError(Exception):
                    status_code = 404
                raise SimulatedTransportError("secret token 123")
            return FakeDeco.request(fake, path, form, data)
        fake.request = request
        result = self.controller(fake).poll()
        self.assertEqual(result.mobile_blacklist.status, "request_error")
        self.assertEqual(result.mobile_blacklist.error_type, "SimulatedTransportError")
        self.assertEqual(result.mobile_blacklist.http_status_code, 404)
        self.assertNotIn("secret", str(result.mobile_blacklist))
        self.assertEqual(fake.operations, [])

    def test_mobile_app_blacklist_failure_does_not_disable_base_poll(self):
        fake = FakeDeco(blocked={MAC_A})
        fake.mobile_read_failure = True
        result = self.controller(fake).poll()
        self.assertEqual(result.mobile_blacklist.status, "request_error")
        self.assertIsNone(result.mobile_blacklist_macs)
        self.assertEqual(result.blocked, frozenset({MAC_A}))
        self.assertEqual(fake.operations, [])

    def test_blocklist_missing_field_aborts_without_writes(self):
        fake = FakeDeco()
        fake.malformed_blocklist = True
        with self.assertRaises(DecoAccessError):
            self.controller(fake).set_allowed(MAC_A, False)
        self.assertEqual(fake.operations, [])

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
