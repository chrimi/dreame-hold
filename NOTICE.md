# Provenance

`custom_components/dreame_hold/dreame_cloud/` (`cloud_base.py`,
`cloud_device.py`) is adapted from two MIT-licensed upstream projects, each
with its own copyright as noted below. LICENSE (MIT) governs this
repository's own original code.

- **Original protocol implementation**: [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum),
  Copyright (c) 2022 Tasshack. That project is scoped to robot vacuums;
  this one extends the same underlying Dreame/MOVA cloud API to the
  handheld ("hold") product line, the same way
  [antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower)
  and [bhuebschen/dreame-mower](https://github.com/bhuebschen/dreame-mower)
  extend it to lawn mowers.
- **Extracted/refactored cloud transport layer**: [antondaubert/dreame-mower](https://github.com/antondaubert/dreame-mower),
  Copyright (c) 2025 Anton Daubert. The cloud login/MQTT/`get_properties`
  code has no mower-specific logic (only the class names did), so it was
  reusable unmodified for a handheld device.

Everything else in this repository (the property map in `const.py`,
`coordinator.py`, `entity.py`, `sensor.py`, `binary_sensor.py`,
`config_flow.py`) is original, built from scratch by empirically probing a
Dreame H14 Pro (model `dreame.hold.w2306f`) with the tools in `dev/` — see
`FINDINGS.md` at the repo root for the evidence behind each property's
meaning.

`custom_components/dreame_hold/brand/` (`icon.png`, `icon@2x.png`,
`logo.png`, `logo@2x.png`, `dark_logo.png`, `dark_logo@2x.png`) is
Dreame's official trademark/logo, byte-identical to the assets
`Tasshack/dreame-vacuum` and `antondaubert/dreame-mower` use for the same
purpose (identifying the device manufacturer, not this project). Sourced
from [home-assistant/brands](https://github.com/home-assistant/brands)'s
`custom_integrations/dreame_vacuum/` entry. Per Home Assistant's Brands
Proxy API (2026.3+), custom integrations ship these locally instead of
submitting a PR to that repository — see
[the announcement](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api).

## Changes made to the adapted files

Classes renamed `DreameMowerCloud*` → `DreameCloud*` (no functional
change). The `ActionIdentifier` type, originally imported from a
`homeassistant`-coupled `const.py` in the mower project, is redefined
locally in `cloud_device.py` so this integration's cloud layer has no
transitive dependency beyond what's declared in `manifest.json`.
