"""Constants for the Dreame Hold (handheld vacuum) integration.

The siid/piid property map below is reverse-engineered empirically — see
FINDINGS.md in the dreame-h14-probe companion tool for the snapshot-by-
snapshot evidence. It is confirmed against a single device
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

# Batch of properties polled every coordinator refresh. Kept small and
# specific (rather than re-sweeping the full siid/piid space) to avoid
# hammering the cloud API on every poll — use dreame-h14-probe's
# probe_properties.py separately to explore further properties.
POLLED_PROPERTIES: Final = [
    PROP_BATTERY_LEVEL,
    PROP_STATUS,
    PROP_STATUS_MIRROR,
    PROP_ACTIVITY_PROGRESS,
    PROP_ACTIVITY_DURATION,
    PROP_SELFCLEAN_ELAPSED,
]

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
