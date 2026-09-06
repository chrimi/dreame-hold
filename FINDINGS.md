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
| `1:64`, `1:65`, `1:66` | **Time (seconds) spent on light / moderate / heavy soiling** during the last vacuum run | confirmed | `307 + 54 + 3 = 364` — exactly matches `1:22` (total run duration). Floor-percentages `floor(307/364*100)=84`, `floor(54/364*100)=14`, remainder `100-84-14=2` — exactly matches the app's own reported breakdown "84% leicht, 14% moderat, 2% stark" (the classic "round first two, remainder gets the rest" display trick). |
| `1:68`, `1:69` | Other last-vacuuming-session statistics (dust/motor stats?) — exact meaning unknown | likely | `0` before any vacuuming; `110`, `254` right after the run; frozen (unchanged) through subsequent snapshots — written once at end of a vacuum session, not live counters. Don't sum to `1:22` or to each other in an obviously meaningful way yet. |
| `1:22` | **Duration (seconds) of the last vacuuming run** | confirmed | `364` exactly matches the owner-reported second cleaning run of the day: 13:09, "6 minutes 4 seconds" = 6*60+4 = 364. `0` while idle/charging; back to `0` during self-clean (resets per new operation, unlike the frozen `1:64` etc.). The first run of the day (13:00, 4 seconds) wasn't captured in a snapshot, so summation across multiple runs per day is untested. |
| `1:31` | Drying-specific sub-value (temperature/fan stage?) | guess | `0` everywhere except during drying, where it was `3`. |
| `1:32` | Unknown — possibly time-since-last-full-cycle or a health stat | guess | `0` until the final idle-on-dock-after-cycle snapshot, where it became `59`. |
| `1:3` | **Device light switch** (`0`=off, `1`=on) | confirmed | `0 -> 1` when the owner "switched on light", `1 -> 0` when they turned it back off — bidirectionally confirmed. The light-on probe also caught `16:6` flipping back to `0` (Benutzerdefiniert off) as an apparent unintentional side effect of app navigation, not something the owner reported doing. |
| `1:14` | **Voice announcement volume** (0-100 scale, presumably) | confirmed | `0 -> 30` when volume was changed from 0 to "something > 0", then cleanly isolated `30 -> 0` when set back to 0 — nothing else changed in that second step. |
| `1:17` | **Voice announcement language**: `English=2, Deutsch=3, Français=4, [unused]=5, Italiano=6, Español=7, ..., Arabic=13, Hebrew=14, [unused]=15, Dutch=16` | confirmed | Tracked cleanly through eight consecutive single-setting language changes: de(3)->en(2)->fr(4)->it(6)->es(7)->nl(16)->he(14)->ar(13), nothing else changed in any of these steps. Fixed internal language-ID table with gaps, not app-menu order. **These 8 values are all the languages this app/device offered to select** — the gaps (`5`, `8-12`, `15`) are internal enum values with no corresponding option in this app instance/region, not values we failed to test. Not pursuing this further. |
| `16:1` | **Saugleistung (suction power)**: `leicht=1, Standard=2, stark=3` | confirmed | Isolated test: changing only Saugleistung (Standard->leicht) changed only this property (`2->1`). Not visible until siid 16 was discovered via a wider sweep (`--siid-max 20`/`--siids`) — outside the original siid 1-8 range. |
| `16:2` | **Wasserstand (water level)**: `täglich=1, [unnamed]=2, nass=3` | confirmed | Isolated test: changing only Wasserstand (täglich->nass) changed only this property (`1->3`). The third value `2` showed up as the implied water level under "Leiser Modus" — all 3 values of the ordinal now observed, though the app's label for `2` isn't confirmed (Leiser Modus doesn't expose an explicit Wasserstand picker). Stays at its last explicit value when switching between preset modes rather than always resetting (e.g. stayed `3`/nass when switching Personalisiert->Turbomodus) — except presets can also imply their own value (Leiser Modus implied `2`). |
| `23:1` | **Self propulsion force adjustment**: `Balanced=0, soft=1, strong=2` | confirmed | Only discovered by widening the sweep to `--siid-max 30` (not present anywhere in siid 1-20). Full ordinal enum confirmed: first read was `1` (soft), isolated `1 -> 0` when set back to "Balanced" (nothing else changed), then `0 -> 2` when set to "strong". |
| `16:7` | **Active cleaning-mode selector**: `Leiser Modus=1, Turbomodus=3, Personalisiert=4` (value `2` not yet captured) | likely | Tracks the top-level mode: `4` across all Personalisiert snapshots, `3` under Turbomodus, `1` under Leiser Modus. `16:1` (Saugleistung) moves with it too (`1`/leicht under Leiser Modus, `3`/stark under Turbomodus) — presets imply both Saugleistung and Wasserstand values. Sticky: keeps its last value (`1`) even after "Benutzerdefiniert" is turned off — doesn't reset to a distinct "off" sentinel. |
| `16:6` | **"Benutzerdefiniert" (custom cleaning mode) master on/off flag** (`0`=off, `1`=on) | confirmed | Isolated test: turning "Benutzerdefiniert" off changed only `16:6` (`1->0`); `16:7` (sub-mode) stayed at its last value. Turning it back on (to "Leiser Modus") flipped it back `0->1`, alongside `16:3` (see below) — retroactively also explains the earlier unexplained `0->1` jump between the first two siid-16 snapshots. |
| `16:3` | **"Prepare Electrolyzed Water" toggle** (`0`=on, `1`=off) | likely | `1 -> 0` when this setting was enabled, alongside turning "Benutzerdefiniert" back on (to Leiser Modus) in the same step — but `16:6` alone fully accounts for the Benutzerdefiniert part of that change, leaving `16:3` as the one property attributable to the electrolyzed-water toggle. Same `0`=on/`1`=off convention as `1:7`/`1:9`. Not as cleanly isolated as the other siid-16 entries (two settings changed at once) — a fully isolated test would help confirm. |
| `1:9` | **"Automatische Walzenbürstentrocknung" disabled flag** (`0`=on/default, `1`=off) | likely | `0 -> 1` exactly when this setting was turned off in the app. Turning it off also reset `1:12`/`1:13` (the scheduled-drying start time/pattern) to `0` — suggests "Automatische Walzenbürstentrocknung" is a parent toggle that the "Planmäßige Walzenbürstentrocknung" schedule depends on, not an independent setting. |
| `1:7` | **"Automatische Selbstreinigung" disabled flag** (`0`=on, `1`=off) | likely | `1 -> 0` exactly when this setting (previously off by default) was turned on in the app. Same `0`=on/`1`=off convention as `1:9`, transition in the opposite direction (off->on here vs on->off there) — consistent pattern across both "Automatische ..." toggles. |
| `1:8` and `1:10` | **Drying mode setting** (quiet / super-speed / ...) | confirmed | Jumped together `2->3` when "Trocknungsmodus" was set to "Super-Speed-Modus", and back `3->2` when reverted to "leiser Modus" — confirmed bidirectionally. |
| `1:12` | **Scheduled drying start time**, seconds since midnight | confirmed | `0 -> 54000` when "Planmäßige Walzenbürstentrocknung" was enabled with start time 15:00. `54000 = 15*3600` — exact match. |
| `1:13` | **Scheduled drying repeat pattern**: bit 0 = "one-time/no repeat" flag, bits 1-7 = weekday enabled (Mon..Sun) when repeating | confirmed | `0 -> 1110111` (i.e. `01110111` — the leading 0 is dropped since this is transmitted as an integer) for "daily except Thursday": bit0=`0` (is a repeating schedule), Mon..Sun=`1,1,1,0,1,1,1` (Thursday off) — exact match. Then `1110111 -> 10000000` when the daily repeat was turned off (one-time schedule): bit0=`1` (one-time flag set), all weekday bits `0` (irrelevant for a one-shot run) — confirms bit0's meaning. |

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

## Negative result: cleaning/suction mode settings not in siid 1-8 / piid 1-120

Tested a full chain of settings under what looks like a "Reinigungsmodus"
(cleaning mode) area — "Benutzerdefiniert" toggle, "Leiser Modus",
"Turbomodus", "Personalisierter Modus" (with its own "Saugleistung"
[Standard/leicht/stark] and "Wasserstand" [täglich/nass] sub-settings) —
each isolated to one changed setting per probe. **None of these changed
any property in the currently swept range** (siid 1-8, piid 1-120) — only
`1:47` (the live timestamp) moved. Resolved below: a wider sweep found
these live at higher siids.

## Wider sweep (siid 1-20, piid 1-250) — new services found

`dev/logs/probe_20260905_171837.json` (17:18:37) swept siid 1-20, piid
1-250 for the first time and found three siids not visible in the
previous siid 1-8 range:

| siid:piid | Value | Notes |
|---|---|---|
| `16:1` | `3` | |
| `16:2` | `3` | |
| `16:3` | `1` | |
| `16:4` | `0` | |
| `16:5` | `0` | |
| `16:6` | `0` | |
| `16:7` | `4` | |
| `17:8` | `0` | |
| `19:1` | `0` | |
| `19:2` | `3600` | |
| `19:3` | `3592` | |

`siid 16` (7 properties) is the leading candidate for the whole
"Reinigungsmodus" block (Benutzerdefiniert/Leiser/Turbo/Personalisiert
with Saugleistung+Wasserstand — a similar count of distinct settings).
`siid 19` has the same `(0, ~3600, ~3600-ish)` shape as `siid 6`/`siid 7`
— a third instance of that still-unexplained mirrored-timer pattern.

**Update — mapped via isolated tests** (using the new `--siids` flag, see
README): `16:1` (Saugleistung), `16:2` (Wasserstand), `16:6`
("Benutzerdefiniert" on/off) and `16:7` (active sub-mode) are now
confirmed/likely-mapped — see the main table above. Still open:

- `16:4`, `16:5`, `17:8` — not yet correlated with anything.
- `16:7` value `2` isn't captured yet (`Leiser Modus=1, Turbomodus=3,
  Personalisiert=4` are).

## Known issue: "Detergent Proportioning Mode" not located

Setting is on the same device-settings screen as "Self propulsion force
adjustment" (`23:1`, confirmed above), default value "Smart
Proportioning", tried changing to "Powerful stain removal". Searched and
found nothing:

- `siid` 1-20 / `piid` 1-250 (the full previously-known range)
- `siid` 20-30 / `piid` 1-20 (same siid as propulsion, and neighbors)

Both settings reverted to their defaults (Smart Proportioning, Balanced)
without resolving this. Not pursued further for now — would need either a
much wider blind sweep (e.g. `siid` 1-50) or a different search strategy
to locate it.

## Live write-path testing (via the built integration, not dev/ probing)

First real test of `DreameCloudDevice.set_property` against the physical
device, through the actual `switch`/`select` entities built into
`custom_components/dreame_hold`. Confirms writing settings works in
principle. Specific findings:

- **`PROP_CLEANING_MODE` (`16:7`) cannot be set directly.** Selecting
  "quiet" or "turbo" via the select entity did not switch the device's
  actual mode. Likely explanation: it's a read-only reflection of
  `PROP_SUCTION_POWER`/`PROP_WATER_LEVEL` rather than an independently
  settable property — consistent with it being sticky/derived (see the
  `16:7` entry above). The integration now exposes it as a read-only
  sensor instead of a select. **Not yet root-caused** — would need
  probing what "quiet"/"turbo" actually set `16:1`/`16:2` to (try writing
  those two directly to see if that's what really switches the mode) or
  checking whether mode-switching uses an `action` (siid/aiid) call
  instead of `set_property`.
- **`PROP_ELECTROLYZED_WATER_DISABLED` (`16:3`) only works while
  `PROP_CUSTOM_MODE_ENABLED` (`16:6`) is on.** Confirmed on the real
  device — modeled in the integration as an `available`/unavailable
  dependency between the two switch entities.
- **`PROP_WATER_LEVEL`'s (`16:2`) `level_2` value is not a real
  Personalized-Mode choice.** The app's own water-level picker under
  "Personalized Mode" only offers two options ("daily"/"wet") — `level_2`
  only ever appeared as a side effect of selecting "Leiser Modus". Kept
  decodable for reading, removed from the select entity's offered
  options.
- **App UI grouping** (useful context, not a functional issue): in the
  real app, "Wash & Dry" groups Drying mode + Automatic self-clean +
  Automatic roller brush drying + Scheduled roller brush drying (now
  built as `time.<name>_scheduled_drying_time` +
  `switch.<name>_scheduled_drying_*`, but with the write direction
  unverified — see README's "Known limitations").
  "Custom mode" groups quiet/turbo/personalized, with Water level and
  Suction power as Personalized-Mode-only sub-settings, and Prepare
  Electrolyzed Water gated on Custom mode being on (per above). Voice
  language and Voice volume are presented together. The owner categorizes
  Voice language, Voice volume, and Self propulsion force as general
  "Device settings", and the rest as "cleaning settings" — this doesn't
  map to anything in the current entity structure (HA has no built-in
  "settings group" concept beyond entity_category CONFIG/DIAGNOSTIC,
  which all of these already use) but is worth keeping in mind for
  future dashboard/documentation organization.

### Scheduled-drying entities: bug found and fixed, root cause confirmed

After building `time.<name>_scheduled_drying_time` and the weekday
switches, the owner reported three issues while testing live: the start
time reverted to 00:00 in the app, HA showed no active schedule while the
app still showed one configured, and the per-day entries appeared out of
order in the UI. Diagnosed directly against the real device (with
temporary, throwaway scripts using credentials the owner provided for
this purpose — never committed, deleted after use):

- **Confirmed the raw write mechanism itself works correctly**:
  `set_property(1, 12, 54000)` took effect immediately and was still
  `54000` after a 5-second delay on read-back. This rules out a bug in
  `DreameCloudDevice.set_property` or the time-to-seconds conversion.
- **Found and fixed a real race condition**: `DreameHoldWeekdaySwitch._set()`
  was computing its read-modify-write base value from the *coordinator's
  polled/cached* property (up to `DEFAULT_SCAN_INTERVAL` seconds stale).
  Toggling two weekday switches back-to-back, faster than a poll cycle,
  let the second write silently overwrite the first with a stale base
  mask. Fixed to fetch a *fresh* value via `get_properties` immediately
  before each write. **Verified live**: toggling Monday then immediately
  Tuesday (no delay) now correctly leaves both set
  (`1:13` read back as `1100000` — decodes to Monday+Tuesday, matching
  `helpers.decode_weekday_mask`) — before the fix this would very likely
  have left only Tuesday set.
- **The device's actual state at the time of the report was `1:12=0,
  1:13=0`** (fully cleared) — confirmed by direct read. Since raw writes
  work and persist, the most likely explanation for "time reverted to
  00:00" and "HA shows nothing, app still shows a schedule" is the
  already-documented `PROP_AUTO_DRYING_DISABLED` side effect (turning
  "Automatic roller brush drying" off resets both properties to 0) having
  been triggered at some point during testing, combined with the app not
  necessarily refreshing its own display immediately after a change made
  by a different client (this integration) rather than itself — the
  latter is a plausible but unconfirmed app-side behavior, not something
  this integration can control either way.
- Also fixed while investigating: weekday switch entity names now get a
  `1`-`7` numeric prefix so Home Assistant's alphabetical entity sort
  still lands in Monday..Sunday order (previously e.g. "Friday" sorted
  before "Monday").
- **Unrelated but discovered in the process**: `sys.path.insert(0, ...)`
  in the `dev/` scripts and `tests/conftest.py` made
  `custom_components/dreame_hold/select.py` and `.../time.py` shadow
  Python's own stdlib `select`/`time` modules, since those files now
  exist (added for the settings entities) and our directory was placed
  *first* on `sys.path`. Any script importing something that transitively
  needs stdlib `select` (e.g. `ssl` → `socket` → `selectors` → `select`)
  after that point would crash with a confusing traceback. Fixed by
  switching to `sys.path.append(...)` everywhere, so the standard library
  is always searched first.

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
  time).

  Update 16:11:58: changing the "Trocknungsmodus" app setting (no power
  button, no dock interaction) also flipped `2:1` from `15` back to `7`.
  Combined with the manual's documented behavior ("device fully enters
  rest mode after 10 min of inactivity"), **revised hypothesis: `2:1`
  7-vs-15 may primarily track wake/sleep state, not charge current** —
  `7` = device is awake/active (triggered by *any* interaction: charging,
  button press, or just an app settings change), `15` = fully asleep
  after ~10 min undisturbed. This would explain the "flapping" better
  than a maintenance-charge-pulse theory, and makes `2:1` even less
  suitable as a charging-automation signal (a mere app check would reset
  it). Not yet confirmed — needs a clean test: touch nothing (no app, no
  button) for >10 min, then probe once, to see if `2:1` settles at `15`
  without any interaction in between.

  Update 16:16:40: ran that clean test — no interaction since the
  16:11:58 drying-mode change, app reporting "Ruhemodus" (resting), but
  `2:1` still reads `7` (unchanged from 16:11:58). **Refutes the simple
  "any interaction sets a fresh 10-minute countdown, then flips to 15"
  hypothesis at face value** — only ~5-8 min had elapsed since the last
  actual write (the drying-mode change), short of the manual's documented
  10-minute threshold, so this result is still consistent with a slower
  internal transition than the app's own "resting" label suggests (the
  app may show "resting" well before the device's internal state actually
  reaches `15`). Needs one more probe at >=10 min after the last write,
  with zero interaction in between, to settle this either way.
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
| 16:11:58 | On dock; "Trocknungsmodus" reverted to "leiser Modus" just before this probe | `dev/logs/probe_20260905_161158.json` |
| 16:16:40 | On dock; no interaction since 16:11:58, app shows "Ruhemodus" | `dev/logs/probe_20260905_161640.json` |
| 16:20:39 | On dock; "Planmäßige Walzenbürstentrocknung" enabled, start 15:00, daily except Thursday; app says this doesn't end rest mode | `dev/logs/probe_20260905_162039.json` |
| 16:24:14 | On dock; same schedule, daily repeat turned off (one-time) | `dev/logs/probe_20260905_162414.json` |
| 16:26:47 | On dock; "Automatische Walzenbürstentrocknung" turned off | `dev/logs/probe_20260905_162647.json` |
| 16:28:53 | On dock; "Automatische Selbstreinigung" turned on (only change) | `dev/logs/probe_20260905_162853.json` |
| 16:32:07 | On dock; "Waschen und Trocknen" settings reset to original baseline (Selbstreinigung aus, Walzenbürstentrocknung ein, Planmäßige Trocknung aus, Trocknungsmodus leise) | `dev/logs/probe_20260905_163207.json` |
| 16:54:01 | On dock; "Benutzerdefiniert" cleaning-mode area enabled, mode "Leiser Modus" | `dev/logs/probe_20260905_165401.json` |
| 16:56:06 | On dock; cleaning mode "Turbomodus" | `dev/logs/probe_20260905_165606.json` |
| 16:59:08 | On dock; cleaning mode "Personalisierter Modus", Saugleistung=Standard, Wasserstand=täglich | `dev/logs/probe_20260905_165908.json` |
| 17:00:41 | On dock; Saugleistung changed to "leicht" | `dev/logs/probe_20260905_170041.json` |
| 17:05:11 | On dock; Saugleistung changed to "stark" | `dev/logs/probe_20260905_170511.json` |
| 17:08:07 | On dock; Wasserstand changed to "nass" | `dev/logs/probe_20260905_170807.json` |
| 17:18:37 | On dock; first wide sweep, siid 1-20 / piid 1-250 (no setting changed since 17:08:07) | `dev/logs/probe_20260905_171837.json` |
| 17:24:03 | On dock; Personalisierter Modus reset to its default (Saugleistung=Standard, Wasserstand=täglich) — combined change vs. previous state | `dev/logs/probe_20260905_172403.json` |
| 17:27:01 | On dock; Saugleistung changed to "leicht" only, Wasserstand held at "täglich" (isolated change) | `dev/logs/probe_20260905_172701.json` |
| 17:29:09 | On dock; Wasserstand changed to "nass" only, Saugleistung held at "leicht" (isolated change) | `dev/logs/probe_20260905_172909.json` |
| 17:34:53 | On dock; cleaning mode switched from Personalisiert to "Turbomodus" | `dev/logs/probe_20260905_173453.json` |
| 17:37:49 | On dock; cleaning mode switched to "Leiser Modus" | `dev/logs/probe_20260905_173749.json` |
| 17:40:44 | On dock; "Benutzerdefiniert" turned off | `dev/logs/probe_20260905_174044.json` |
| 17:42:48 | On dock; "Benutzerdefiniert" turned back on (Leiser Modus) *and* "Prepare Electrolyzed Water" toggle set, in the same step | `dev/logs/probe_20260905_174248.json` |
| 17:45:08 | On dock; device light switched on | `dev/logs/probe_20260905_174508.json` |
| 17:47:32 | On dock; device light switched off again; Sprachansage volume changed from 0 to >0 | `dev/logs/probe_20260905_174732.json` |
| 17:49:45 | On dock; Sprachansage volume set back to 0 | `dev/logs/probe_20260905_174945.json` |
| 17:53:32 | On dock; Sprachansage language changed from Deutsch to English | `dev/logs/probe_20260905_175332.json` |
| 18:15:10 | On dock; Sprachansage language changed to Français | `dev/logs/probe_20260905_181510.json` |
| 18:17:00 | On dock; Sprachansage language changed to Italiano | `dev/logs/probe_20260905_181700.json` |
| 18:17:32 | On dock; Sprachansage language changed to Español | `dev/logs/probe_20260905_181732.json` |
| 18:17:55 | On dock; Sprachansage language changed to Dutch | `dev/logs/probe_20260905_181755.json` |
| 18:18:16 | On dock; Sprachansage language changed to Hebrew | `dev/logs/probe_20260905_181816.json` |
| 18:18:57 | On dock; Sprachansage language changed to Arabic | `dev/logs/probe_20260905_181857.json` |
| 18:24:30 | On dock; wide sweep (siid 1-8,16,17,19) after "Self propulsion force adjustment" set to "soft" (was "Balanced") — no property in this range changed | `dev/logs/probe_20260905_182430.json` |
| 18:32:15 | On dock; re-check at siid 1-20/piid 1-250 (still "soft") — still no change found | `dev/logs/probe_20260905_183215.json` |
| 18:40:15 | On dock; wider sweep piid 1-300 (no siid cap) — found `23:1` for the first time, value `1` (still "soft") | `dev/logs/probe_20260905_184015.json` |
| 19:26:27 | On dock; targeted re-check of `23:1` only, after setting "Self propulsion force adjustment" back to "Balanced" | `dev/logs/probe_20260905_192627.json` |
| 19:27:40 | On dock; targeted re-check of `23:1` only, after setting "Self propulsion force adjustment" to "strong" | `dev/logs/probe_20260905_192740.json` |
| 19:30:04 | On dock; siid 23 (piid 1-20) with "Detergent Proportioning Mode" at its default ("Smart Proportioning") | `dev/logs/probe_20260905_193004.json` |
| 19:30:19 | On dock; siid 23 (piid 1-20), "Detergent Proportioning Mode" changed to "Powerful stain removal" — no change found | `dev/logs/probe_20260905_193019.json` |
| 19:32:22 | On dock; siid 20-30 (piid 1-20), searching for Detergent Proportioning Mode near propulsion | `dev/logs/probe_20260905_193222.json` |
| 19:32:53 | On dock; same range, re-checked — no change found either; both settings then reverted to defaults | `dev/logs/probe_20260905_193253.json` |
