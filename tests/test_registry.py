"""Tests for hub.registry module."""

import logging
from pathlib import Path

from hub.registry import AppInfo, Registry


def _write_manifest(
    app_dir: Path,
    name: str = "testapp",
    display_name: str = "Test App",
    description: str = "A test application",
    version: str = "1.0.0",
    backend_module: str = "app:app",
    active_frontends: list[str] | None = None,
    frontend_configs: dict[str, dict] | None = None,
) -> Path:
    """Write a manifest.toml with configurable fields to a tmp directory."""
    manifest_dir = app_dir / ".squareberg"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / "manifest.toml"

    lines = [
        "[app]",
        f'name = "{name}"',
        f'display_name = "{display_name}"',
        f'description = "{description}"',
        f'version = "{version}"',
        "",
        "[backend]",
        f'module = "{backend_module}"',
    ]

    if active_frontends is not None:
        items = ", ".join(f'"{f}"' for f in active_frontends)
        lines.append("")
        lines.append("[frontend]")
        lines.append(f"active = [{items}]")

        if frontend_configs:
            for fe_name, fe_cfg in frontend_configs.items():
                lines.append("")
                lines.append(f"[frontend.{fe_name}]")
                for k, v in fe_cfg.items():
                    lines.append(f'{k} = "{v}"')

    manifest_path.write_text("\n".join(lines) + "\n")
    return manifest_path


def test_scan_empty_directory(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()
    assert reg.list() == []


def test_scan_finds_app(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "hello"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(
        app_dir,
        name="hello",
        display_name="Hello World",
        description="A test app",
        version="0.1.0",
    )

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    apps = reg.list()
    assert len(apps) == 1
    assert apps[0].name == "hello"
    assert apps[0].display_name == "Hello World"
    assert apps[0].description == "A test app"
    assert apps[0].version == "0.1.0"
    assert apps[0].status == "stopped"
    assert apps[0].socket_path == str(socket_dir / "hello.sock")


def test_scan_ignores_invalid(tmp_path):
    apps_dir = tmp_path / "apps"
    # Directory with no manifest
    no_manifest_dir = apps_dir / "invalid-app"
    no_manifest_dir.mkdir(parents=True)

    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()
    assert reg.list() == []


def test_scan_duplicate_name(tmp_path, caplog):
    apps_dir = tmp_path / "apps"
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    # Create two app dirs with the same manifest name
    app1 = apps_dir / "app-a"
    app1.mkdir(parents=True)
    _write_manifest(app1, name="duplicate")

    app2 = apps_dir / "app-b"
    app2.mkdir(parents=True)
    _write_manifest(app2, name="duplicate")

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    with caplog.at_level(logging.WARNING, logger="squareberg.registry"):
        reg.scan()

    # Only one should be registered
    assert len(reg.list()) == 1
    assert any("Duplicate app name" in msg for msg in caplog.messages)


def test_get_existing(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "myapp"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(app_dir, name="myapp")

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    info = reg.get("myapp")
    assert info is not None
    assert info.name == "myapp"


def test_get_nonexistent(tmp_path):
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()
    assert reg.get("nope") is None


def test_set_status(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "myapp"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(app_dir, name="myapp")

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    reg.set_status("myapp", "running")
    assert reg.get("myapp").status == "running"


def test_to_dict(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "myapp"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(app_dir, name="myapp", display_name="My App", description="desc", version="2.0.0")

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    d = reg.get("myapp").to_dict()
    expected_keys = {
        "name", "display_name", "description", "version",
        "status", "socket_path", "frontend_dist_path",
        "manifest_path", "backend_module",
    }
    assert set(d.keys()) == expected_keys
    assert d["name"] == "myapp"
    assert d["display_name"] == "My App"
    assert d["version"] == "2.0.0"


def test_frontend_dist_resolution(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "feapp"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(
        app_dir,
        name="feapp",
        active_frontends=["default"],
        frontend_configs={"default": {"path": "frontend/default", "display_name": "Default"}},
    )

    # Create the dist directory
    dist_dir = app_dir / "frontend" / "default" / "dist"
    dist_dir.mkdir(parents=True)

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    info = reg.get("feapp")
    assert info is not None
    assert info.frontend_dist_path == str(dist_dir)


def test_frontend_dist_missing(tmp_path):
    apps_dir = tmp_path / "apps"
    app_dir = apps_dir / "feapp"
    app_dir.mkdir(parents=True)
    socket_dir = tmp_path / "sockets"
    socket_dir.mkdir()

    _write_manifest(
        app_dir,
        name="feapp",
        active_frontends=["default"],
        frontend_configs={"default": {"path": "frontend/default", "display_name": "Default"}},
    )

    # Do NOT create the dist directory

    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()

    info = reg.get("feapp")
    assert info is not None
    assert info.frontend_dist_path is None
