"""Shared pytest setup.

Tests import `dreame_cloud` and `helpers` directly (not via
`custom_components.dreame_hold...`) so they never trigger
custom_components/dreame_hold/__init__.py, which imports `homeassistant` -
not something these pure-Python unit tests require. Same pattern the dev/
scripts use. See README.md's "Unit tests" section.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.append(str(REPO_ROOT / "custom_components" / "dreame_hold"))
sys.path.append(str(REPO_ROOT / "dev"))
