# Dreame H14 (`dreame.hold.w2306f`) — property findings

Empirical property map built by comparing successive `dev/probe_properties.py`
snapshots (`dev/logs/probe_*.json`) against known physical device state.
Method: change exactly one thing about the device, re-probe, diff. See the
"Exploring further properties" section in README.md.

Confidence levels: **confirmed** (matched an independently known value, e.g.
the device's own reported battery %, or observed across 3+ consistent
snapshots), **likely** (consistent pattern across 2 snapshots), **guess**
(plausible but unverified).

## Confirmed / likely properties

| siid:piid | Meaning | Confidence | Evidence |
|---|---|---|---|
| `3:1` | **Battery level (%)** | confirmed | Full sequence across all 6 snapshots: `100, 100, 86, 85, 82, 100`. Matches the device/app's own displayed value at every point the owner checked it directly (85% and, later, 100%), and the shape is physically coherent: near 100 while idle/charging (including the normal Li-ion "top-off" phase where the app already shows 100% while charge current is still tapering), dipping under the heavy current draw of self-clean+drying, recovering back to 100 after >1h further charging on the dock. **Use this for battery-level automations.** |
| `3:4` | Unclear — not battery level | superseded | Originally mistaken for battery level based on one coincidental exact match (85% at 13:08). Full sequence `89, 80, 85, 85, 86, 88` never reaches 100 even when the device is confirmed fully charged, and rises only 2 points across the >1h charging window before the final snapshot — implausible for a live SoC reading. Possibly a secondary cell, a state-of-health value, or a smoothed/lagging average. Left unresolved. |
| `2:1` (mirrored at `1:28`) | **Activity/status code** | confirmed, but see caveat | Same value at both locations in every snapshot. Values observed so far: `3`=idle/standby (off dock, not charging), `7`=charging or a brief maintenance top-off pulse, `26`=self-clean running, `25`=drying running, `15`=idle/resting (not currently drawing charge current). **Caveat (see Open questions): `7` and `15` both occur at genuine 100% battery** — the device appears to cycle briefly back to `7` for maintenance charging even once full. **Do not use `2:1==7` alone as a smart-plug cutoff signal** — use sustained `3:1>=100` instead (see binary_sensor.py docstring). |
| `1:29` | **Progress % of the current special activity** (self-clean/drying) | likely | `0` when idle/charging; `10` early in self-clean; `90` late in drying; back to `0` once idle again. Meaningless/`0` outside self-clean/drying. |
| `1:56` | **Configured duration (seconds) of the active special activity** | likely | `1800` (30 min) during idle/charging/self-clean; `3600` (60 min) during drying. Possibly the duration setting of whichever mode is/was last active. |
| `1:57` | **Elapsed seconds of the last self-clean run** | likely | `0` before any self-clean; jumped to `220` during self-clean; stayed frozen at `220` through the following drying snapshot (didn't reset until self-clean runs again). |
| `1:64, 1:65, 1:66, 1:68, 1:69` | **Last vacuuming-session statistics** (runtime/dust/motor stats — exact units unknown) | likely | All `0` before any vacuuming; jumped to `307, 54, 3, 110, 254` right after an actual vacuum run; stayed frozen (unchanged) through subsequent self-clean/drying/idle snapshots — i.e. written once at end of a vacuum session, not live counters. |
| `1:22` | Live runtime counter of the *current* operation (vacuuming specifically) | guess | `0` while idle/charging; `364` right after vacuuming (plausibly seconds of that run); back to `0` during self-clean. Distinct from the frozen `1:64` etc. — this one looks like it resets per new operation rather than persisting. |
| `1:31` | Drying-specific sub-value (temperature/fan stage?) | guess | `0` everywhere except during drying, where it was `3`. |
| `1:32` | Unknown — possibly time-since-last-full-cycle or a health stat | guess | `0` until the final idle-on-dock-after-cycle snapshot, where it became `59`. |
| `1:8` and `1:10` | **Drying mode setting** (quiet / super-speed / ...) | likely | Both jumped together from `2` to `3` when "Trocknungsmodus" was changed from "leiser Modus" to "Super-Speed-Modus" in the app, mirrored at two piids like the `2:1`/`1:28` status pair. Only one transition observed so far — not yet confirmed to toggle back. |

## Ruled out

| siid:piid | Was suspected | Why ruled out |
|---|---|---|
| `1:25` | Battery level | Constant at `52` across battery levels of 100%, 85%, 86%, 88% (per corrected `3:1`) — clearly unrelated to battery. |

## Device architecture note

`siid 1` (51 properties) and `siid 2` only respond while the device has been
recently active (charging on the dock, or just used) — they were completely
absent in one snapshot taken right after power-on with the device sitting
idle off the dock with no recent activity. `siid 3, 4, 6, 7` responded in
every snapshot regardless of dock/power state. Working theory: the handheld
unit itself has no persistent network connection; live status is only
synced to the cloud during an active charging or use session, while a
smaller set of values (battery %, drying-timer defaults, etc.) are cached
independently. Not fully pinned down — noted here so it isn't re-discovered
from scratch later.

The 160824 snapshot contains 6 duplicate `(siid, piid)` entries — `1:28,
1:29, 1:56, 1:57, 2:1, 3:1` each appear twice, both times with identical
values, appended out of sequence around result index 560-565 (not at
their natural position in the siid/piid sweep order). Harmless — these
are exactly the properties `dev/diff_snapshots.py`/the coordinator care
about, and both copies agree — but worth noting in case it recurs: the
cloud API appears to sometimes echo a "core status" bundle (battery,
activity status, timers) as a bonus alongside an unrelated batch
response.

`siid 6` and `siid 7` are structurally identical (`piid 1`, `6`, `7` with
the same values in both, drifting down by only ~1 unit per several minutes
regardless of what was running) — almost certainly two mirrored instances
of the same thing (perhaps two redundant timer channels, or a
Dreame-vs-generic-MIoT duplicate). Not yet correlated with anything; not
the self-clean/drying timers (those didn't move in step with actual
self-clean/drying activity).

## Open questions

- **Does `2:1` flap between `7` and `15` at 100% battery, or was 15:16:36
  a one-off?** Two snapshots taken ~1h apart, both at confirmed 100%
  battery (owner-verified against the app, both showing "resting" in the
  app) and both on the dock, gave *different* status codes:

  | Timestamp | `3:1` (battery) | `2:1` (status) |
  |---|---|---|
  | 14:17:38 | 100 | `15` |
  | 15:16:36 | 100 | `7` |

  This contradicts the earlier (now retracted) conclusion that `15` is a
  stable "done charging" state and `7` means "still needs to charge, keep
  the plug on." Current best explanation: the charge controller issues
  brief maintenance/top-off pulses even once the battery reads 100% (self-
  discharge compensation), and `2:1` flips to `7` for the duration of each
  pulse, back to `15` (or `3`?) at rest between pulses. **Not confirmed** —
  would need several snapshots taken a few minutes apart while the device
  sits undisturbed at 100% to see the code toggle in place. Until then,
  treat `2:1` as informational only for the "charging done" case; gate any
  power-cutoff automation on `3:1` staying at 100 for a sustained window
  (e.g. 20–30 min) instead of on a single `2:1` reading.

  Update 16:01:40: pressing the device's power button flipped `2:1` back
  from `7` to `15`, and the app's own label switched from "resting" to
  "charging finished" at the same time — some evidence `15` really is the
  "done" state and the app's wording is just inconsistent between `15`
  occurrences (calling it "resting" once, "charging finished" another
  time). Still unconfirmed whether `2:1` flips to `7` on its own
  (periodic maintenance pulse) without any button press — that's the next
  test to run (leave the device undisturbed at 100% for 10-15 min and
  re-probe).
- What do `6:*`/`7:*` actually represent?
- Exact units/meaning of `1:22`, `1:29`, `1:31`, `1:32`, `1:64/65/66/68/69`.
- What `3:4` actually measures (see Ruled out / superseded above).

## Snapshot log

| Timestamp | Physical state | File |
|---|---|---|
| 12:45:57 | On dock, actively charging | `dev/logs/probe_20260905_124557_charging.json` |
| 12:57:31 | Off dock, was fully charged before removal, device had been fully powered off and manually restarted | `dev/logs/probe_20260905_125731.json` |
| 13:08:32 | Off dock, just used (vacuumed), device reports 85% battery | `dev/logs/probe_20260905_130832.json` |
| 13:11:10 | On dock, self-clean running | `dev/logs/probe_20260905_131110.json` |
| 13:14:47 | On dock, drying running (after self-clean) | `dev/logs/probe_20260905_131447.json` |
| 14:17:38 | On dock, idle, self-clean+dry cycle finished | `dev/logs/probe_20260905_141738.json` |
| 15:16:36 | On dock, 100% battery (app-confirmed), app shows "resting" | `dev/logs/probe_20260905_151636.json` |
| 16:01:40 | On dock, 100% battery, right after pressing the device's power button; app switched from "resting" to "charging finished" | `dev/logs/probe_20260905_160140.json` |
| 16:08:24 | On dock; app setting "Trocknungsmodus" changed from "leiser Modus" to "Super-Speed-Modus" just before this probe | `dev/logs/probe_20260905_160824.json` |
