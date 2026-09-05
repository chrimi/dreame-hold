#!/usr/bin/env python3
"""Probe a Dreame device's REST properties to discover which siid/piid exist.

Sweeps a configurable siid/piid range via batched get_properties calls and
reports which ones return code=0 (supported), with their current value.
Use this against a device's `did` (get it from list_devices.py) to build a
property map for battery, charging, self-clean, drying, water tank etc.

Usage:
    python3 dev/probe_properties.py --device-id 123456789
    python3 dev/probe_properties.py --device-id 123456789 --siid-max 10 --piid-max 50
    python3 dev/probe_properties.py --device-id 123456789 --siid 2 --piid-max 100
    python3 dev/probe_properties.py --device-id 123456789 --siids 1-8,16,17,19

Results are printed to stdout and saved to dev/logs/probe_<TIMESTAMP>.json

Adapted from antondaubert/dreame-mower's dev/probe_rest_properties.py
(MIT license). See NOTICE.md at the repo root for full attribution.
"""

import argparse
import getpass
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DEV_DIR = Path(__file__).parent
REPO_ROOT = DEV_DIR.parent
# Import dreame_cloud directly (not via `custom_components.dreame_hold...`) so
# this script doesn't trigger dreame_hold/__init__.py, which imports
# `homeassistant` — not something a standalone probe script should require.
sys.path.insert(0, str(REPO_ROOT / "custom_components" / "dreame_hold"))

from dreame_cloud.cloud_device import DreameCloudDevice

BATCH_SIZE = 20  # properties per get_properties call
VALID_COUNTRIES = ["eu", "cn", "us", "ru", "sg"]
VALID_ACCOUNT_TYPES = ["dreame", "mova"]


def parse_int_spec(spec: str) -> list[int]:
    """Parse "1-8,16,17,19" into [1,2,3,4,5,6,7,8,16,17,19] (sorted, deduped)."""
    values: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            start, end = int(start_str), int(end_str)
            values.update(range(start, end + 1))
        else:
            values.add(int(part))
    return sorted(values)


def probe(device: DreameCloudDevice, siids: list[int], piid_range: range) -> list[dict[str, Any]]:
    """Sweep all (siid, piid) pairs and return a list of result dicts."""
    pairs = [(s, p) for s in siids for p in piid_range]
    results: list[dict[str, Any]] = []

    for batch_start in range(0, len(pairs), BATCH_SIZE):
        batch = pairs[batch_start: batch_start + BATCH_SIZE]
        params = [{"siid": s, "piid": p} for s, p in batch]
        label = f"siid {batch[0][0]}:{batch[0][1]} .. {batch[-1][0]}:{batch[-1][1]}"
        print(f"  Probing {label} ...", end="", flush=True)
        try:
            result_list = device.get_properties(params)
        except TimeoutError as e:
            print(f" TIMEOUT ({e})")
            for s, p in batch:
                results.append({"siid": s, "piid": p, "code": None, "status": "timeout"})
            time.sleep(2)
            continue
        except Exception as e:
            print(f" ERROR ({e})")
            for s, p in batch:
                results.append({"siid": s, "piid": p, "code": None, "status": f"exception: {e}"})
            continue

        if not isinstance(result_list, list):
            print(f" unexpected response: {result_list!r}")
            continue

        ok_count = 0
        for item in result_list:
            siid = item.get("siid")
            piid = item.get("piid")
            code = item.get("code", -1)
            if code == 0:
                ok_count += 1
                results.append({
                    "siid": siid,
                    "piid": piid,
                    "code": code,
                    "status": "ok",
                    "value": item.get("value"),
                })
            else:
                results.append({"siid": siid, "piid": piid, "code": code, "status": "error"})
        print(f" {ok_count}/{len(batch)} ok")
        time.sleep(0.3)  # avoid hammering the API

    return results


def _prompt_choice(prompt: str, options: list, default: str) -> str:
    opts = ", ".join(options)
    while True:
        val = input(f"{prompt} [{opts}] (default: {default}): ").strip() or default
        if val in options:
            return val
        print(f"Invalid value. Choose one of: {opts}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe a Dreame device's REST properties")
    parser.add_argument("--username", default=None)
    parser.add_argument("--country", default=None, choices=VALID_COUNTRIES)
    parser.add_argument("--account-type", default=None, choices=VALID_ACCOUNT_TYPES)
    parser.add_argument("--device-id", required=True, help="'did' of the device, from list_devices.py")
    parser.add_argument(
        "--siids",
        default=None,
        help="siids to probe, e.g. '1-8,16,17,19' (comma-separated values and/or ranges). "
        "Skips the empty siids in between instead of sweeping every value from min to max. "
        "Overrides --siid/--siid-min/--siid-max when given.",
    )
    parser.add_argument("--siid", type=int, default=None, help="Probe only this siid")
    parser.add_argument("--siid-min", type=int, default=1, help="First siid to probe (default: 1)")
    parser.add_argument("--siid-max", type=int, default=8, help="Last siid to probe (default: 8)")
    parser.add_argument("--piid-min", type=int, default=1, help="First piid to probe (default: 1)")
    parser.add_argument("--piid-max", type=int, default=120, help="Last piid to probe (default: 120)")
    args = parser.parse_args()

    username = args.username or input("Username (email): ").strip()
    password = getpass.getpass("Password: ")
    country = args.country or _prompt_choice("Region", VALID_COUNTRIES, "eu")
    account_type = args.account_type or _prompt_choice("Account type", VALID_ACCOUNT_TYPES, "dreame")

    print(f"Connecting as {username} (device {args.device_id}, {country}) ...")
    device = DreameCloudDevice(
        username=username,
        password=password,
        country=country,
        account_type=account_type,
        device_id=args.device_id,
    )
    # Fetches the device's host/uid/model, which send() needs to build the
    # correct API relay URL — without it every call returns None.
    if not device._initialize_mqtt_connection_state():
        print("Connection / device init failed. Check the device-id and credentials.")
        sys.exit(1)
    print(f"Connected. host={device._host} model={device._model}\n")

    if args.siids:
        siids = parse_int_spec(args.siids)
    elif args.siid:
        siids = [args.siid]
    else:
        siids = list(range(args.siid_min, args.siid_max + 1))
    piid_range = range(args.piid_min, args.piid_max + 1)

    print(f"Probing siid={siids}, piid={args.piid_min}..{args.piid_max} "
          f"({len(siids) * len(piid_range)} pairs in batches of {BATCH_SIZE})\n")

    results = probe(device, siids, piid_range)

    supported = [r for r in results if r["status"] == "ok"]
    print(f"\n{'='*60}")
    print(f"Supported properties ({len(supported)} found):")
    print(f"{'='*60}")
    for r in supported:
        val = r["value"]
        val_str = json.dumps(val, ensure_ascii=False)
        if len(val_str) > 80:
            val_str = val_str[:77] + "..."
        print(f"  {r['siid']:>2}:{r['piid']:<3}  {val_str}")

    out_dir = DEV_DIR / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"probe_{ts}.json"
    out_path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now().astimezone().isoformat(),
                "device_id": args.device_id,
                "model": device._model,
                "siids": siids,
                "piid_range": [piid_range.start, piid_range.stop - 1],
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nFull results saved to {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
