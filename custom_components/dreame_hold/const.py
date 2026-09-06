"""Constants for the Dreame Hold (handheld vacuum) integration.

The siid/piid property map below is reverse-engineered empirically — see
FINDINGS.md at the repo root for the snapshot-by-snapshot evidence. It is
confirmed against a single device
(model dreame.hold.w2306f, the H14 Pro) and may not hold for every
dreame.hold.* / mova.hold.* model; treat unmapped status codes as unknown
rather than erroring, since other models or firmware revisions will likely
expose codes we haven't observed yet.
"""
from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "dreame_hold"
LOGGER = logging.getLogger(__package__)

MANUFACTURER: Final = "Dreame"

CONF_ACCOUNT_TYPE: Final = "account_type"
CONF_DEVICE_ID: Final = "device_id"
CONF_MODEL: Final = "model"

ACCOUNT_TYPE_DREAME: Final = "dreame"
ACCOUNT_TYPE_MOVA: Final = "mova"
ACCOUNT_TYPES: Final = [ACCOUNT_TYPE_DREAME, ACCOUNT_TYPE_MOVA]

COUNTRIES: Final = ["eu", "cn", "us", "ru", "sg"]
DEFAULT_COUNTRY: Final = "eu"

DEFAULT_SCAN_INTERVAL: Final = 60  # seconds

# --- Property map: (siid, piid) tuples -------------------------------------
# Confirmed against the device's own reported battery % and against physical
# state changes triggered on purpose (dock on/off, self-clean, drying).
PROP_BATTERY_LEVEL: Final = (3, 1)
"""Battery level (%). Confirmed: matched the device/app's own displayed
value at 85% and 100% across multiple snapshots, and its trajectory
(100→100→86→85→82→100) is physically coherent with charge/discharge."""

PROP_STATUS: Final = (2, 1)
"""Activity/status code. Mirrored identically at siid 1, piid 28 in every
snapshot observed. See STATUS_* constants for known values."""

PROP_STATUS_MIRROR: Final = (1, 28)
"""Same value as PROP_STATUS in every snapshot so far; kept as a fallback
in case a future firmware/model only exposes one of the two."""

PROP_ACTIVITY_PROGRESS: Final = (1, 29)
"""Progress % of the currently active special activity (self-clean or
drying). 0 when idle/charging/vacuuming; rose from 10 to 90 across a single
self-clean-then-drying sequence."""

PROP_ACTIVITY_DURATION: Final = (1, 56)
"""Configured duration (seconds) of the currently/most-recently active
special activity. Observed 1800 (30 min) at rest/self-clean, 3600 (60 min)
during drying — likely per-activity, not confirmed as a fixed constant."""

PROP_SELFCLEAN_ELAPSED: Final = (1, 57)
"""Elapsed seconds of the last self-clean run. 0 before any self-clean,
otherwise frozen at the value reached when self-clean last ran."""

PROP_LAST_RUN_DURATION: Final = (1, 22)
"""Duration (seconds) of the last vacuuming run. Confirmed exactly against
an owner-reported run: 364 = 6 min 4 sec. Resets to 0 for the next
operation (self-clean, etc.), unlike the frozen 1:64/1:65/1:66 below."""

PROP_SOILING_LIGHT: Final = (1, 64)
PROP_SOILING_MODERATE: Final = (1, 65)
PROP_SOILING_HEAVY: Final = (1, 66)
"""Time (seconds) spent on light/moderate/heavy soiling during the last
vacuum run. PROP_SOILING_LIGHT + _MODERATE + _HEAVY == PROP_LAST_RUN_DURATION
exactly (307+54+3=364), and their floor-percentages match the app's own
reported breakdown (84%/14%/2%) via the "remainder to last" display
convention. Frozen (like PROP_LAST_RUN_DURATION's siblings) until the next
vacuum run."""

PROP_LIGHT_SWITCH: Final = (1, 3)
"""Device light on/off: 0=off, 1=on. Confirmed bidirectionally."""

PROP_VOICE_VOLUME: Final = (1, 14)
"""Voice announcement volume, 0-100 (presumed scale). Confirmed
bidirectionally (0 <-> 30 in testing)."""

PROP_VOICE_LANGUAGE: Final = (1, 17)
"""Voice announcement language. See LANGUAGE_NAMES. Fixed internal
language-ID table with gaps, not sequential app-menu order."""

PROP_AUTO_SELFCLEAN_DISABLED: Final = (1, 7)
"""'Automatische Selbstreinigung' disabled flag: 0=on, 1=off."""

PROP_AUTO_DRYING_DISABLED: Final = (1, 9)
"""'Automatische Walzenbürstentrocknung' disabled flag: 0=on, 1=off.
Automatically dries the roller brush right after a self-clean cycle -
independent of PROP_SCHEDULED_DRYING_TIME/_WEEKDAYS (the time-of-day
schedule), confirmed by two live tests: writing this property directly
does not touch the schedule properties either way, and separately
isolating the app's own "Scheduled roller brush drying" toggle showed it
writes PROP_SCHEDULED_DRYING_TIME/_WEEKDAYS directly with no third
property involved. An earlier version of this docstring claimed a
parent/child relationship based on a single probe snapshot where both
happened to change together - that was two separate app actions
landing in one snapshot, not a causal link; see FINDINGS.md."""

PROP_DRYING_MODE: Final = (1, 8)
PROP_DRYING_MODE_MIRROR: Final = (1, 10)
"""'Trocknungsmodus': see DRYING_MODE_NAMES. Mirrored at two piids like
PROP_STATUS/PROP_STATUS_MIRROR; write both when setting."""

PROP_SCHEDULED_DRYING_TIME: Final = (1, 12)
"""Scheduled drying start time, seconds since midnight (54000 = 15:00:00
exactly). 0 when no schedule is set - confirmed this is also exactly how
the app's own "Scheduled roller brush drying" off-switch represents
"disabled": isolating that one toggle (with every other siid=1/16
property monitored live) showed it write this property AND
PROP_SCHEDULED_DRYING_WEEKDAYS to 0 together, with nothing else
involved - there's no separate boolean "enabled" property."""

PROP_SCHEDULED_DRYING_WEEKDAYS: Final = (1, 13)
"""Scheduled drying repeat pattern as an 8-digit string (transmitted as an
int, so a leading 0 is dropped in the raw value): digit 0 = "one-time, no
repeat" flag, digits 1-7 = Mon..Sun enabled. See helpers.py's
encode_weekday_mask/decode_weekday_mask. The write direction is less
confirmed than most other properties here - only the read/decode side
has been verified against real values; see FINDINGS.md's "Live write-path
testing" section."""

PROP_SUCTION_POWER: Final = (16, 1)
"""'Saugleistung': see SUCTION_POWER_NAMES."""

PROP_WATER_LEVEL: Final = (16, 2)
"""'Wasserstand': see WATER_LEVEL_NAMES. Sticky - keeps its last value
when switching to a preset cleaning mode rather than always resetting."""

PROP_CUSTOM_MODE_ENABLED: Final = (16, 6)
"""'Benutzerdefiniert' master on/off flag for the cleaning-mode area:
0=off, 1=on. Confirmed via isolated test."""

PROP_CLEANING_MODE: Final = (16, 7)
"""Active cleaning sub-mode: see CLEANING_MODE_NAMES. Sticky - keeps its
last value even after PROP_CUSTOM_MODE_ENABLED is turned off."""

PROP_ELECTROLYZED_WATER_DISABLED: Final = (16, 3)
"""'Prepare Electrolyzed Water' disabled flag: 0=on, 1=off. Confidence:
likely, not cleanly isolated (changed alongside PROP_CUSTOM_MODE_ENABLED
in the one test done so far) - see FINDINGS.md."""

PROP_PROPULSION_FORCE: Final = (23, 1)
"""'Self propulsion force adjustment': see PROPULSION_FORCE_NAMES. Only
found by widening the sweep to siid 23 - not present in siid 1-20."""

# Batch of properties polled every coordinator refresh. Kept to properties
# we actually expose as entities (rather than re-sweeping the full
# siid/piid space) to avoid hammering the cloud API on every poll — use
# dev/probe_properties.py separately to explore further properties.
POLLED_PROPERTIES: Final = [
    PROP_BATTERY_LEVEL,
    PROP_STATUS,
    PROP_STATUS_MIRROR,
    PROP_ACTIVITY_PROGRESS,
    PROP_ACTIVITY_DURATION,
    PROP_SELFCLEAN_ELAPSED,
    PROP_LAST_RUN_DURATION,
    PROP_SOILING_LIGHT,
    PROP_SOILING_MODERATE,
    PROP_SOILING_HEAVY,
    PROP_LIGHT_SWITCH,
    PROP_VOICE_VOLUME,
    PROP_VOICE_LANGUAGE,
    PROP_AUTO_SELFCLEAN_DISABLED,
    PROP_AUTO_DRYING_DISABLED,
    PROP_DRYING_MODE,
    PROP_DRYING_MODE_MIRROR,
    PROP_SCHEDULED_DRYING_TIME,
    PROP_SCHEDULED_DRYING_WEEKDAYS,
    PROP_SUCTION_POWER,
    PROP_WATER_LEVEL,
    PROP_CUSTOM_MODE_ENABLED,
    PROP_CLEANING_MODE,
    PROP_ELECTROLYZED_WATER_DISABLED,
    PROP_PROPULSION_FORCE,
]

# --- Enums for the settings entities ----------------------------------------
# All empirically observed on one H14 Pro (dreame.hold.w2306f) via dev/
# probing - see FINDINGS.md. Values not in these maps surface as a
# generic fallback rather than erroring (other models/firmware/regions
# likely expose values not seen here, e.g. more languages).

DRYING_MODE_NAMES: Final[dict[int, str]] = {2: "quiet", 3: "super_speed"}

SUCTION_POWER_NAMES: Final[dict[int, str]] = {1: "light", 2: "standard", 3: "strong"}

WATER_LEVEL_NAMES: Final[dict[int, str]] = {1: "daily", 2: "level_2", 3: "wet"}
"""'level_2' is a placeholder - only confirmed as an implied value under
"Leiser Modus", the app never showed an explicit label for it."""

CLEANING_MODE_NAMES: Final[dict[int, str]] = {1: "quiet", 3: "turbo", 4: "personalized"}
"""Value 2 not yet observed."""

PROPULSION_FORCE_NAMES: Final[dict[int, str]] = {0: "balanced", 1: "soft", 2: "strong"}

LANGUAGE_NAMES: Final[dict[int, str]] = {
    2: "english",
    3: "german",
    4: "french",
    6: "italian",
    7: "spanish",
    13: "arabic",
    14: "hebrew",
    16: "dutch",
}
"""Fixed internal language-ID table with gaps (not sequential app-menu
order) - these 8 are all the languages this app/device offered to
select, not necessarily all values the property can hold."""

# --- Status code enum --------------------------------------------------------
# Empirically observed on one H14 Pro (dreame.hold.w2306f). Codes not in this
# map are surfaced as "unknown_<code>" rather than raised as an error, since
# other models/firmware almost certainly have codes we haven't seen yet
# (e.g. water-tank-full, dustbin-full, or other error conditions).
STATUS_IDLE: Final = 3
STATUS_CHARGING: Final = 7
STATUS_DRYING: Final = 25
STATUS_SELF_CLEANING: Final = 26
STATUS_DOCKED_IDLE: Final = 15
"""Device on the dock, battery full, no self-clean/drying running — a
stable resting state, not transient (confirmed against battery=100%)."""

STATUS_NAMES: Final[dict[int, str]] = {
    STATUS_IDLE: "idle",
    STATUS_CHARGING: "charging",
    STATUS_DRYING: "drying",
    STATUS_SELF_CLEANING: "self_cleaning",
    STATUS_DOCKED_IDLE: "docked_idle",
}

# Status codes under which the device is actually drawing charge current.
# Used to derive the "is charging" binary sensor — this is the exact signal
# the original use case (cutting power to a smart plug once charging is
# done) needs.
CHARGING_STATUS_CODES: Final = {STATUS_CHARGING}
