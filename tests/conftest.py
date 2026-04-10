"""Pytest configuration and shared fixtures for the squareberg-hub test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_EXAMPLES_HELLO = _PROJECT_ROOT / "examples" / "hello"


@pytest.fixture(scope="session", autouse=True)
def isolated_xdg_home(tmp_path_factory):
    """Point XDG_DATA_HOME at a temp directory with the hello app symlinked in.

    This ensures tests are hermetic — they don't depend on what is (or isn't)
    installed in the developer's or CI runner's real data directory.
    """
    tmp = tmp_path_factory.mktemp("xdg_data")
    apps_dir = tmp / "squareberg" / "apps"
    apps_dir.mkdir(parents=True)
    (apps_dir / "hello").symlink_to(_EXAMPLES_HELLO, target_is_directory=True)

    original = os.environ.get("XDG_DATA_HOME")
    os.environ["XDG_DATA_HOME"] = str(tmp)

    yield tmp

    if original is None:
        os.environ.pop("XDG_DATA_HOME", None)
    else:
        os.environ["XDG_DATA_HOME"] = original
