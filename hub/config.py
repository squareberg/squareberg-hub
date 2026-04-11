"""Hub configuration loading and directory resolution."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("squareberg.config")

# ---------------------------------------------------------------------------
# TOML parsing — use stdlib tomllib on 3.11+, fall back to tomli
# ---------------------------------------------------------------------------
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as exc:
        raise ImportError(
            "tomli is required on Python <3.11. Install it with: pip install tomli"
        ) from exc


def _read_toml(path: Path) -> dict:
    """Read and parse a TOML file."""
    with open(path, "rb") as fh:
        return tomllib.load(fh)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _hub_root() -> Path:
    """Return the hub/ directory (the directory containing this file)."""
    return Path(__file__).resolve().parent


def _project_root() -> Path:
    """Return the squareberg project root (parent of hub/)."""
    return _hub_root().parent


# ---------------------------------------------------------------------------
# Config dataclass
# ---------------------------------------------------------------------------

@dataclass
class HubConfig:
    host: str = "127.0.0.1"
    port: int = 9100
    socket_mode: str = "xdg"  # "xdg" or "local"
    log_level: str = "info"
    log_dir: Optional[str] = None


def load_config(path: Path | None = None) -> HubConfig:
    """Load hub configuration from a TOML file.

    Defaults to the user config at ``$XDG_CONFIG_HOME/squareberg/config.toml``.
    Falls back to built-in defaults if the file does not exist.
    """
    if path is None:
        path = get_config_path()

    if not path.exists():
        logger.debug("Config file not found at %s; using defaults.", path)
        return HubConfig()

    logger.debug("Loading config from %s", path)
    data = _read_toml(path)
    hub = data.get("hub", {})
    sockets = hub.get("sockets", {})
    logging_cfg = hub.get("logging", {})

    log_dir_raw = logging_cfg.get("dir", "") or None

    return HubConfig(
        host=hub.get("host", "127.0.0.1"),
        port=hub.get("port", 9100),
        socket_mode=sockets.get("mode", "xdg"),
        log_level=logging_cfg.get("level", "info"),
        log_dir=log_dir_raw,
    )


# ---------------------------------------------------------------------------
# Directory helpers
# ---------------------------------------------------------------------------

def _xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_config_dir() -> Path:
    """Return the user config directory under XDG_CONFIG_HOME."""
    return _xdg_config_home() / "squareberg"


def get_config_path() -> Path:
    """Return the path to the user's config.toml under XDG_CONFIG_HOME."""
    return get_config_dir() / "config.toml"


def get_default_config_path() -> Path:
    """Return the path to the bundled default config (read-only, in site-packages)."""
    return _hub_root() / "config.toml"


def ensure_user_config() -> Path:
    """Copy the bundled default config to the user config path if missing.

    Returns the user config path.
    """
    user_path = get_config_path()
    if user_path.exists():
        return user_path

    user_path.parent.mkdir(parents=True, exist_ok=True)
    default_path = get_default_config_path()
    if default_path.exists():
        shutil.copy(default_path, user_path)
        logger.info("Created user config at %s", user_path)
    return user_path


def get_socket_dir(config: HubConfig | None = None) -> Path:
    """Resolve the socket directory and create it if needed."""
    mode = config.socket_mode if config else "xdg"

    if mode == "xdg":
        sock_dir = _xdg_data_home() / "squareberg" / "sockets"
    else:
        sock_dir = _project_root() / "sockets"

    sock_dir.mkdir(parents=True, exist_ok=True)
    return sock_dir


def get_log_dir(config: HubConfig | None = None) -> Path:
    """Resolve the log directory and create it if needed."""
    if config and config.log_dir:
        log_dir = Path(config.log_dir)
    else:
        log_dir = _xdg_data_home() / "squareberg" / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_apps_dir() -> Path:
    """Return the apps directory under XDG_DATA_HOME, creating it if needed."""
    apps_dir = _xdg_data_home() / "squareberg" / "apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    return apps_dir


def get_examples_dir() -> Path:
    """Return the in-tree examples/ directory (sibling of hub/)."""
    return _hub_root().parent / "examples"
