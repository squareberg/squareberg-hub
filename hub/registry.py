"""App registry — discovers and tracks installed Squareberg apps."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("squareberg.registry")

# TOML parsing
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError as exc:
        raise ImportError(
            "tomli is required on Python <3.11. Install it with: pip install tomli"
        ) from exc


@dataclass
class AppInfo:
    name: str
    display_name: str
    description: str
    version: str
    status: str = "stopped"
    socket_path: Optional[str] = None
    frontend_dist_path: Optional[str] = None
    manifest_path: Optional[str] = None
    backend_module: Optional[str] = None
    app_dir: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "status": self.status,
            "socket_path": self.socket_path,
            "frontend_dist_path": self.frontend_dist_path,
            "manifest_path": self.manifest_path,
            "backend_module": self.backend_module,
        }


class Registry:
    """Discovers apps from the filesystem and tracks their runtime status."""

    def __init__(self, apps_dir: Path, socket_dir: Path) -> None:
        self._apps_dir = apps_dir
        self._socket_dir = socket_dir
        self._apps: dict[str, AppInfo] = {}

    # ------------------------------------------------------------------
    # Scanning
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Scan apps_dir and the in-tree examples/ directory for apps."""
        self._apps.clear()

        # Scan the runtime apps/ directory
        if self._apps_dir.is_dir():
            self._scan_directory(self._apps_dir)

        # Scan in-tree examples/ directory (sibling of hub/)
        from .config import get_examples_dir
        examples_dir = get_examples_dir()
        if examples_dir.is_dir():
            self._scan_directory(examples_dir)

        logger.info(
            "Registry scan complete: %d app(s) found — %s",
            len(self._apps),
            ", ".join(self._apps.keys()) or "(none)",
        )

    def _scan_directory(self, directory: Path) -> None:
        """Scan a directory for subdirectories containing .squareberg/manifest.toml."""
        for child in sorted(directory.iterdir()):
            if not child.is_dir():
                continue
            manifest = child / ".squareberg" / "manifest.toml"
            if manifest.is_file():
                self._load_manifest(manifest, child)

    def _load_manifest(self, manifest_path: Path, app_dir: Path) -> None:
        """Parse a manifest.toml and register the app."""
        try:
            with open(manifest_path, "rb") as fh:
                data = tomllib.load(fh)
        except Exception:
            logger.warning("Failed to parse manifest: %s", manifest_path, exc_info=True)
            return

        app_section = data.get("app", {})
        backend_section = data.get("backend", {})
        frontend_section = data.get("frontend", {})

        name = app_section.get("name", app_dir.name)

        # Resolve the active frontend dist path
        frontend_dist: str | None = None
        active_frontends = frontend_section.get("active", [])
        if active_frontends:
            first_active = active_frontends[0]
            fe_config = frontend_section.get(first_active, {})
            fe_rel_path = fe_config.get("path", f"frontend/{first_active}")
            dist_candidate = app_dir / fe_rel_path / "dist"
            if dist_candidate.is_dir():
                frontend_dist = str(dist_candidate)

        socket_path = str(self._socket_dir / f"{name}.sock")

        info = AppInfo(
            name=name,
            display_name=app_section.get("display_name", name),
            description=app_section.get("description", ""),
            version=app_section.get("version", "0.0.0"),
            status="stopped",
            socket_path=socket_path,
            frontend_dist_path=frontend_dist,
            manifest_path=str(manifest_path),
            backend_module=backend_section.get("module", "app:app"),
            app_dir=str(app_dir),
        )

        if name in self._apps:
            logger.warning("Duplicate app name '%s'; skipping %s", name, app_dir)
            return

        self._apps[name] = info
        logger.debug("Registered app: %s (%s)", name, app_dir)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get(self, name: str) -> AppInfo | None:
        return self._apps.get(name)

    def list(self) -> list[AppInfo]:
        return list(self._apps.values())

    def set_status(self, name: str, status: str) -> None:
        if name in self._apps:
            self._apps[name].status = status
