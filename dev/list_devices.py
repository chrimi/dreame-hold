#!/usr/bin/env python3
"""List all devices on your Dreame/MOVA cloud account, to find a device's `did`.

Usage:
    python3 dev/list_devices.py
    python3 dev/list_devices.py --username you@example.com --country eu

Adapted from antondaubert/dreame-mower's dev/list_devices.py (MIT license).
See NOTICE.md at the repo root for full attribution.
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
# Import dreame_cloud directly (not via `custom_components.dreame_hold...`) so
# this script doesn't trigger dreame_hold/__init__.py, which imports
# `homeassistant` — not something a standalone probe script should require.
sys.path.insert(0, str(ROOT_DIR / "custom_components" / "dreame_hold"))

from dreame_cloud.cloud_device import DreameCloudDevice

VALID_COUNTRIES = ["eu", "cn", "us", "ru", "sg"]
VALID_ACCOUNT_TYPES = ["dreame", "mova"]


def _prompt_choice(prompt: str, options: list, default: str) -> str:
    opts = ", ".join(options)
    while True:
        val = input(f"{prompt} [{opts}] (default: {default}): ").strip() or default
        if val in options:
            return val
        print(f"Invalid value. Choose one of: {opts}")


def main():
    parser = argparse.ArgumentParser(description="List Dreame/MOVA devices for your account")
    parser.add_argument("--username", default=None, help="Cloud username (email); prompted if omitted")
    parser.add_argument("--country", default=None, choices=VALID_COUNTRIES)
    parser.add_argument("--account-type", default=None, choices=VALID_ACCOUNT_TYPES)
    args = parser.parse_args()

    username = args.username or input("Username (email): ").strip()
    password = getpass.getpass("Password: ")
    country = args.country or _prompt_choice("Region", VALID_COUNTRIES, "eu")
    account_type = args.account_type or _prompt_choice("Account type", VALID_ACCOUNT_TYPES, "dreame")

    client = DreameCloudDevice(
        username=username,
        password=password,
        country=country,
        account_type=account_type,
        device_id="",  # not needed for listing
    )

    if not client._cloud_base.connect():
        print("Login failed. Check username/password/country.")
        raise SystemExit(1)

    devices = client._cloud_base.get_devices()
    print(json.dumps(devices, indent=2, ensure_ascii=False))
    print(
        "\nLook for your handheld device by its 'model' (handheld models seen "
        "so far contain '.hold.', e.g. dreame.hold.w2306f) and note its 'did' "
        "— that's the --device-id you pass to probe_properties.py."
    )


if __name__ == "__main__":
    main()
