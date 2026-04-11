"""Pytest configuration and shared fixtures for the squareberg-hub test suite."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_EXAMPLES_HELLO = _PROJECT_ROOT / "examples" / "hello"


@pytest.fixture(scope="session", autouse=True)
def isolated_xdg_home(tmp_path_factory):
    """Point XDG_DATA_HOME and XDG_CONFIG_HOME at temp directories.

    This ensures tests are hermetic — they don't depend on what is (or isn't)
    installed in the developer's or CI runner's real XDG directories. The
    hello example app is symlinked into the temp data dir so registry-based
    tests can find it.
    """
    data_tmp = tmp_path_factory.mktemp("xdg_data")
    config_tmp = tmp_path_factory.mktemp("xdg_config")

    apps_dir = data_tmp / "squareberg" / "apps"
    apps_dir.mkdir(parents=True)
    (apps_dir / "hello").symlink_to(_EXAMPLES_HELLO, target_is_directory=True)

    saved = {
        "XDG_DATA_HOME": os.environ.get("XDG_DATA_HOME"),
        "XDG_CONFIG_HOME": os.environ.get("XDG_CONFIG_HOME"),
    }
    os.environ["XDG_DATA_HOME"] = str(data_tmp)
    os.environ["XDG_CONFIG_HOME"] = str(config_tmp)

    yield data_tmp

    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
