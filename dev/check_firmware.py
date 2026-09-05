#!/usr/bin/env python3
"""Check a Dreame device's firmware version via the cloud OTA endpoint.

Unlike battery/status/settings, firmware info isn't a siid/piid property —
it's a separate cloud API call (checkDeviceVersion) that DreameCloudDevice
already exposes as check_device_version(). No sweeping needed.

Usage:
    python3 dev/check_firmware.py --device-id 123456789
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

DEV_DIR = Path(__file__).parent
REPO_ROOT = DEV_DIR.parent
# Import dreame_cloud directly (not via `custom_components.dreame_hold...`) so
# this script doesn't trigger dreame_hold/__init__.py, which imports
# `homeassistant` — not something a standalone script should require.
sys.path.insert(0, str(REPO_ROOT / "custom_components" / "dreame_hold"))

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Check a Dreame device's firmware version")
    parser.add_argument("--username", default=None)
    parser.add_argument("--country", default=None, choices=VALID_COUNTRIES)
    parser.add_argument("--account-type", default=None, choices=VALID_ACCOUNT_TYPES)
    parser.add_argument("--device-id", required=True, help="'did' of the device, from list_devices.py")
    parser.add_argument(
        "--lang",
        default=None,
        help="Optional language for the response's release-notes text (e.g. 'en', 'en_US', 'de'). "
        "Without it, the 'description' field comes back as a cloud error blob instead of text — "
        "the exact expected value format isn't confirmed, this is for experimenting.",
    )
    parser.add_argument(
        "--lang-in-query",
        action="store_true",
        help="Send --lang as a URL query parameter (?lang=...) instead of in the JSON body. "
        "Try this if the body version still returns the 'missing lang' error.",
    )
    args = parser.parse_args()

    username = args.username or input("Username (email): ").strip()
    password = getpass.getpass("Password: ")
    country = args.country or _prompt_choice("Region", VALID_COUNTRIES, "eu")
    account_type = args.account_type or _prompt_choice("Account type", VALID_ACCOUNT_TYPES, "dreame")

    device = DreameCloudDevice(
        username=username,
        password=password,
        country=country,
        account_type=account_type,
        device_id=args.device_id,
    )
    if not device._initialize_mqtt_connection_state():
        print("Connection / device init failed. Check the device-id and credentials.")
        sys.exit(1)
    print(f"Connected. model={device._model}\n")

    version_info = device.check_device_version(lang=args.lang, lang_in_query=args.lang_in_query)
    if version_info is None:
        print("No version info returned (unexpected response from checkDeviceVersion).")
        sys.exit(1)

    print(json.dumps(version_info, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
