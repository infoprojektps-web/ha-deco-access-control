# Deco Access Control for Home Assistant (BETA)

Custom Home Assistant integration for individual TP-Link Deco client access switches, using local API and `tplink-deco-api==2.0.0`.

**Experimental:** only offline mocked tests have passed. Hardware compatibility with mixed M4/X50 Deco in AP mode is **not verified**.

## Features

- One switch for each discovered device: ON = Wi-Fi permitted; OFF = blocked on Deco Wi-Fi.
- Reads block list before and after any write, validates responses and confirms requested state.
- Uses individual-MAC API operations; this custom integration never directly rewrites the full list.
- Serializes write operations and polling.
- Switches disabled by default; enable only selected test devices.

## HACS installation

1. HACS → ⋮ → Custom repositories → `https://github.com/infoprojektps-web/ha-deco-access-control` → Integration.
2. Download; restart HA.
3. Settings → Devices & services → Add integration → Deco Access Control.
4. Enter the IP of the main Deco (previously identified as `192.168.0.205`, verify), username `admin`, current owner password and scan interval `60`.
5. In entity registry, search `Dostęp Wi-Fi`; enable **one** nonessential test client entity.
6. Turn OFF, verify in official Deco app, then turn ON and verify unblock.

Do not expose router passwords or session tokens. **Change the Deco password shown in your earlier screenshot.**

## Requirements and limitations

- Home Assistant 2026.10+, Python 3.14+, pinned `tplink-deco-api==2.0.0`.
- Hardware API and owner authentication are **untested** here; firmware can change behavior.
- Blocking is Wi-Fi association control, not internet-only filtering. Ethernet and other Wi-Fi access paths are unaffected.
- Existing blocklist should be recorded before testing; do not test on your administrative device.
- Private/randomized MAC addresses can bypass static MAC rules if changed.
- Disable old `deco_manager` during testing to avoid session conflicts.

## Technical tests

```bash
python -m unittest discover -s tests -v
```

Mock tests do not prove router compatibility. No change is applied to your router by publishing this code.

[Instrukcja po polsku](README_PL.md)

MIT licensed independent wrapper around the public tplink-deco-api SDK interface.