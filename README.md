# Dreame Hold

Home Assistant / HACS custom integration for Dreame handheld ("hold")
vacuum/mop devices (e.g. the H14 / H14 Pro). Extends the same Dreame/MOVA
cloud API that [`Tasshack/dreame-vacuum`](https://github.com/Tasshack/dreame-vacuum)
covers for robot vacuums to this device class instead — the same relationship
the [dreame-mower](https://github.com/antondaubert/dreame-mower) forks have
to it for lawn mowers. See NOTICE.md for full provenance.

**Status: early / v1.** Confirmed working against one device (H14 Pro,
model `dreame.hold.w2306f`). Entities:

- `sensor.<name>_battery` — battery level (%)
- `binary_sensor.<name>_charging` — on exactly while the device is drawing
  charge current; the intended trigger for "cut power to the charging smart
  plug once charging is done" automations
- `sensor.<name>_status` — decoded activity status (idle / charging /
  self_cleaning / drying / docked_idle / unknown), with the raw numeric
  code as an attribute
- `sensor.<name>_activity_progress` — progress % while self-clean or drying
  is running

See `custom_components/dreame_hold/const.py` for the exact siid/piid
property map and its confidence level, and [`FINDINGS.md`](FINDINGS.md) for
the snapshot-by-snapshot evidence behind each one. Properties beyond what's
listed there are unmapped — use the probing tools in [`dev/`](dev/) to
explore further and extend `const.py`/`sensor.py` accordingly.

## Installation

### Via HACS (custom repository)

This isn't in HACS's default store — add it as a custom repository:

1. HACS → three-dot menu (top right) → **Custom repositories**.
2. Repository: `https://github.com/chrimi/dreame-hold`, type: **Integration**.
3. Find "Dreame Hold" in HACS → Integrations and install it.
4. Restart Home Assistant.
5. Settings → Devices & Services → Add Integration → "Dreame Hold".

### Manual (alternative)

1. Copy `custom_components/dreame_hold` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → "Dreame Hold".

### Setting up the integration (either install method)

Once you start the config flow, enter your Dreame/MOVA app email + password.

**If you normally sign in via "Sign in with Google" (or another
third-party login):** that won't work here. Open the Dreamehome app →
profile/account settings → set a password for your account, then use that
email + the new password. (Confirmed workaround from
[Tasshack/dreame-vacuum#1580](https://github.com/Tasshack/dreame-vacuum/issues/1580).)

If your account has multiple handheld devices, you'll be asked to pick the
right one.

## Exploring further properties (`dev/`)

`dev/` holds the standalone (no Home Assistant needed) tools used to build
the property map in `const.py`, following the same pattern
[antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower)
uses for its `dev/` folder:

```bash
cd dev
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 list_devices.py                          # find your device's `did`
python3 probe_properties.py --device-id <did>     # sweep siid/piid -> logs/probe_*.json
python3 diff_snapshots.py logs/A.json logs/B.json # compare two snapshots
```

Change exactly one thing about the device's physical state between two
probes (dock it, start self-clean, empty the water tank, ...) and diff —
whatever changed is almost certainly tied to that state change. See
`FINDINGS.md` for the full log of what's been tried and found so far.

## Known limitations / open items

- Only one physical device (H14 Pro) has been used to build the property
  map — other `dreame.hold.*`/`mova.hold.*` models may expose different
  siid/piid numbers or additional status codes. The status sensor falls
  back to `unknown` for any code it doesn't recognize instead of erroring,
  specifically to stay usable on models/firmware with codes we haven't
  seen.
- No error/fault sensors yet (e.g. water tank full, dustbin full,
  self-clean/drying error) — not yet triggered/observed during probing.
- Polls the cloud REST API on a fixed interval (default 60s) rather than
  using the device's MQTT push channel — simpler and sufficient for a
  battery/status/charging use case; revisit if lower latency is needed.
- Device-list parsing in `config_flow.py` (`_extract_hold_devices`) infers
  the response shape generically rather than from documented field names
  (all field names are obfuscated in the upstream cloud API) — flag it if
  device discovery fails on an account with an unusual structure.

## License

MIT — see LICENSE and NOTICE.md for full attribution to the upstream
projects this was built on.
