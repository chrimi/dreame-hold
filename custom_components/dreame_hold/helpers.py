"""Pure-Python helper functions with no Home Assistant dependency.

Kept separate from entity.py/sensor.py/config_flow.py so they can be
unit-tested without installing the homeassistant package — see tests/.
"""
from __future__ import annotations

from typing import Any

# A device belongs to the H-series handheld line if its model string
# contains this marker (e.g. "dreame.hold.w2306f", confirmed on an H14 Pro).
# Other handheld models/regions may use a different marker; widen this if a
# real device turns up that doesn't match.
HOLD_MODEL_MARKER = ".hold."


def extract_hold_devices(devices_response: Any) -> list[dict[str, Any]]:
    """Pull the flat device list out of the cloud's getDevices response and
    keep only handheld ("hold") models.

    Confirmed shape (from decoding the obfuscated API string table used by
    DreameCloudDevice.get_device_info, which indexes the same response as
    `devices["page"]["records"]`): a dict with a "page" object containing
    a "records" list of device dicts, each with at least 'did' and
    'model'. Falls back to a generic nested-dict/list scan for safety, in
    case a different account/region ever returns a different shape.
    """
    if not isinstance(devices_response, dict):
        return []

    page = devices_response.get("page")
    if isinstance(page, dict):
        records = page.get("records")
        if isinstance(records, list):
            candidates = [item for item in records if isinstance(item, dict) and "did" in item]
            return [d for d in candidates if HOLD_MODEL_MARKER in str(d.get("model", ""))]

    # Fallback: generic scan, in case the confirmed shape above doesn't match.
    candidates: list[dict[str, Any]] = []
    for value in devices_response.values():
        if isinstance(value, dict):
            for inner in value.values():
                if isinstance(inner, list):
                    candidates.extend(item for item in inner if isinstance(item, dict) and "did" in item)
        elif isinstance(value, list):
            candidates.extend(item for item in value if isinstance(item, dict) and "did" in item)

    return [d for d in candidates if HOLD_MODEL_MARKER in str(d.get("model", ""))]


def soiling_percentages(light: int, moderate: int, heavy: int) -> tuple[int, int, int] | None:
    """Return (light_pct, moderate_pct, heavy_pct) for a vacuuming run.

    Uses the same "floor the first two, remainder to the last" convention
    the Dreame app itself uses — confirmed against a real run to reproduce
    the app's own displayed breakdown (84%/14%/2% for 307/54/3 seconds)
    exactly. Independent per-value rounding wouldn't guarantee the three
    percentages sum to 100.

    Returns None if there's no run data yet (all zero).
    """
    total = light + moderate + heavy
    if total <= 0:
        return None

    light_pct = light * 100 // total
    moderate_pct = moderate * 100 // total
    heavy_pct = 100 - light_pct - moderate_pct
    return light_pct, moderate_pct, heavy_pct


WEEKDAYS: tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
"""Order matches PROP_SCHEDULED_DRYING_WEEKDAYS' digit order (confirmed:
"daily except Thursday" decoded to Mon,Tue,Wed,Thu,Fri,Sat,Sun =
1,1,1,0,1,1,1)."""


def decode_weekday_mask(value: int) -> dict[str, bool]:
    """Decode PROP_SCHEDULED_DRYING_WEEKDAYS' 8-digit repeat mask.

    Transmitted as a plain int, so a leading 0 (the normal case: a
    repeating schedule) is dropped from the wire value — pad back to 8
    digits before splitting. Digit 0 is a "one-time, no repeat" flag;
    digits 1-7 are Monday..Sunday enabled. Confirmed against two real
    values: `1110111` (padded `01110111`) for "daily except Thursday",
    and `10000000` for "repeat off" (one_time=True, no days).

    Returns a dict with keys "one_time" plus one per WEEKDAYS entry.
    """
    digits = str(value).zfill(8)
    result: dict[str, bool] = {"one_time": digits[0] == "1"}
    for i, day in enumerate(WEEKDAYS):
        result[day] = digits[i + 1] == "1"
    return result


def encode_weekday_mask(days: dict[str, bool], one_time: bool = False) -> int:
    """Inverse of decode_weekday_mask. `days` maps weekday name -> enabled;
    a day missing from `days` is treated as disabled.

    CAUTION: only the two real values above have been confirmed to
    round-trip correctly. Writing this property back to the device with a
    freshly-encoded value has not been tested (see FINDINGS.md's "Live
    write-path testing" section) — the write direction for the scheduled-
    drying feature is more speculative than the rest of this integration.
    """
    flag = "1" if one_time else "0"
    day_digits = "".join("1" if days.get(day) else "0" for day in WEEKDAYS)
    return int(flag + day_digits)
