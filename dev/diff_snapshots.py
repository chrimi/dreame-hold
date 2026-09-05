#!/usr/bin/env python3
"""Compare two probe_properties.py snapshots and show which siid:piid values changed.

This is the fast way to find out what a property means: capture a baseline,
change one thing about the device's physical state (put it on the dock,
start self-clean, start drying, empty the water tank, ...), capture again,
and diff. Whatever changed is very likely related to that state change.

Usage:
    python3 diff_snapshots.py logs/probe_BEFORE.json logs/probe_AFTER.json
"""

import argparse
import json
from pathlib import Path


def load(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {(r["siid"], r["piid"]): r for r in data["results"] if r["status"] == "ok"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff two probe_properties.py result files")
    parser.add_argument("before", help="Earlier probe_*.json snapshot")
    parser.add_argument("after", help="Later probe_*.json snapshot")
    args = parser.parse_args()

    before = load(args.before)
    after = load(args.after)

    keys = sorted(set(before) | set(after))
    changed = []
    appeared = []
    disappeared = []

    for key in keys:
        b = before.get(key)
        a = after.get(key)
        if b is None:
            appeared.append((key, a["value"]))
        elif a is None:
            disappeared.append((key, b["value"]))
        elif b["value"] != a["value"]:
            changed.append((key, b["value"], a["value"]))

    def fmt(v):
        s = json.dumps(v, ensure_ascii=False)
        return s if len(s) <= 60 else s[:57] + "..."

    print(f"Comparing {args.before} -> {args.after}\n")

    if changed:
        print(f"CHANGED ({len(changed)}):")
        for (siid, piid), b, a in changed:
            print(f"  {siid:>2}:{piid:<3}  {fmt(b)}  ->  {fmt(a)}")
    else:
        print("CHANGED: none")

    if appeared:
        print(f"\nNEWLY SUPPORTED ({len(appeared)}) — only responded in 'after':")
        for (siid, piid), v in appeared:
            print(f"  {siid:>2}:{piid:<3}  {fmt(v)}")

    if disappeared:
        print(f"\nNO LONGER SUPPORTED ({len(disappeared)}) — only responded in 'before':")
        for (siid, piid), v in disappeared:
            print(f"  {siid:>2}:{piid:<3}  {fmt(v)}")

    if not changed and not appeared and not disappeared:
        print("\nNo differences found. Either nothing changed on the device, or the")
        print("property that changed wasn't in the siid/piid range you swept.")


if __name__ == "__main__":
    main()
