"""Squareberg CLI — hub lifecycle, app management, and frontend switching."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

# ---------------------------------------------------------------------------
# TOML parsing — same compat shim as config.py / registry.py
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

from .config import get_apps_dir, get_examples_dir, get_log_dir, get_socket_dir, load_config
from .registry import Registry

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
console = Console()

_config = load_config()
_HUB_URL = f"http://{_config.host}:{_config.port}"


def _uv() -> str:
    """Return the path to the uv binary, or abort with a clear message."""
    path = shutil.which("uv")
    if path is None:
        console.print(
            "[red]uv not found.[/red] Install it from https://docs.astral.sh/uv/ "
            "or ensure it is on your PATH."
        )
        raise typer.Exit(1)
    return path

# ---------------------------------------------------------------------------
# Typer apps
# ---------------------------------------------------------------------------
app = typer.Typer(
    name="squareberg",
    help="Squareberg -- local application hub CLI.",
    no_args_is_help=True,
)

app_cmd = typer.Typer(
    name="app",
    help="Manage installed Squareberg apps.",
    no_args_is_help=True,
)

frontend_cmd = typer.Typer(
    name="frontend",
    help="Manage app frontends.",
    no_args_is_help=True,
)

app.add_typer(app_cmd)
app.add_typer(frontend_cmd)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hub_is_running() -> bool:
    """Check whether the hub API is reachable."""
    try:
        import httpx
        resp = httpx.get(f"{_HUB_URL}/registry", timeout=2.0)
        return resp.status_code == 200
    except Exception:
        return False


def _api_get(path: str) -> dict | list:
    """GET from the hub API. Raises typer.Exit on failure."""
    import httpx
    try:
        resp = httpx.get(f"{_HUB_URL}{path}", timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print("[red]Hub is not running.[/red] Start it with: sqb start")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text
        console.print(f"[red]API error ({exc.response.status_code}):[/red] {detail}")
        raise typer.Exit(1)


def _api_request(method: str, path: str) -> dict:
    """Make a request to the hub API. Raises typer.Exit on failure."""
    import httpx
    try:
        resp = httpx.request(method, f"{_HUB_URL}{path}", timeout=15.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        console.print("[red]Hub is not running.[/red] Start it with: sqb start")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as exc:
        detail = ""
        try:
            detail = exc.response.json().get("detail", "")
        except Exception:
            detail = exc.response.text
        console.print(f"[red]API error ({exc.response.status_code}):[/red] {detail}")
        raise typer.Exit(1)


def _api_post(path: str) -> dict:
    return _api_request("POST", path)


def _api_delete(path: str) -> dict:
    return _api_request("DELETE", path)


def _read_manifest(app_dir: Path) -> dict:
    """Read and return the parsed manifest.toml for an app directory."""
    manifest_path = app_dir / ".squareberg" / "manifest.toml"
    if not manifest_path.is_file():
        console.print(f"[red]Manifest not found:[/red] {manifest_path}")
        raise typer.Exit(1)
    with open(manifest_path, "rb") as fh:
        return tomllib.load(fh)


def _write_manifest(app_dir: Path, data: dict) -> None:
    """Write a manifest dict back to TOML. Uses a simple serialiser."""
    manifest_path = app_dir / ".squareberg" / "manifest.toml"
    lines: list[str] = []
    _toml_dump(data, lines, prefix="")
    manifest_path.write_text("\n".join(lines) + "\n")


def _toml_dump(data: dict, lines: list[str], prefix: str) -> None:
    """Minimal TOML serialiser sufficient for manifest files."""
    # First pass: emit simple key/value pairs at this level
    for key, value in data.items():
        if isinstance(value, dict):
            continue
        lines.append(f"{key} = {_toml_value(value)}")

    # Second pass: emit sub-tables
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        section = f"{prefix}.{key}" if prefix else key
        lines.append("")
        lines.append(f"[{section}]")
        _toml_dump(value, lines, prefix=section)


def _toml_value(value: object) -> str:
    """Format a Python value as a TOML literal."""
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        items = ", ".join(_toml_value(v) for v in value)
        return f"[{items}]"
    return f'"{value}"'


def _offline_registry() -> Registry:
    """Build a Registry by scanning the filesystem (hub not required)."""
    socket_dir = get_socket_dir(_config)
    apps_dir = get_apps_dir()
    reg = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    reg.scan()
    return reg


def _run_cmd(
    cmd: list[str],
    *,
    cwd: Path | str | None = None,
    label: str = "",
) -> None:
    """Run a subprocess, printing output on failure."""
    display = label or " ".join(cmd[:3])
    console.print(f"  [dim]Running:[/dim] {display}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(f"[red]Command failed:[/red] {' '.join(cmd)}")
        if result.stdout.strip():
            console.print(result.stdout)
        if result.stderr.strip():
            console.print(f"[red]{result.stderr}[/red]")
        raise typer.Exit(1)


def _build_frontend(app_dir: Path, fe_rel_path: str) -> None:
    """Run npm install && npm run build in a frontend directory."""
    fe_dir = app_dir / fe_rel_path
    if not fe_dir.is_dir():
        console.print(f"  [yellow]Frontend dir not found, skipping:[/yellow] {fe_dir}")
        return
    pkg_json = fe_dir / "package.json"
    if not pkg_json.is_file():
        console.print(f"  [yellow]No package.json, skipping frontend build:[/yellow] {fe_dir}")
        return
    _run_cmd(["npm", "install"], cwd=fe_dir, label=f"npm install ({fe_dir.name})")
    _run_cmd(["npm", "run", "build"], cwd=fe_dir, label=f"npm run build ({fe_dir.name})")


def _install_backend(app_dir: Path) -> None:
    """Create venv and install backend deps using uv."""
    uv = _uv()
    venv_dir = app_dir / ".venv"
    console.print(f"  [dim]Creating venv:[/dim] {venv_dir}")
    _run_cmd([uv, "venv", "--allow-existing", str(venv_dir)], label="uv venv")
    backend_dir = app_dir / "backend"
    if backend_dir.is_dir():
        _run_cmd(
            [uv, "pip", "install", "-e", str(backend_dir),
             "--python", str(venv_dir / "bin" / "python")],
            cwd=app_dir,
            label="uv pip install -e backend/",
        )
    else:
        console.print("  [yellow]No backend/ directory; skipping dependency install.[/yellow]")


def _build_active_frontends(app_dir: Path, manifest: dict) -> None:
    """Build all active frontends declared in the manifest."""
    frontend_section = manifest.get("frontend", {})
    active = frontend_section.get("active", [])
    for fe_name in active:
        fe_config = frontend_section.get(fe_name, {})
        fe_path = fe_config.get("path", f"frontend/{fe_name}")
        _build_frontend(app_dir, fe_path)


def _find_hub_pids() -> list[int]:
    """Find PIDs of uvicorn processes serving hub.main:app."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn.*hub\\.main:app"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return [int(p) for p in result.stdout.strip().split("\n") if p.strip()]
    except Exception:
        pass
    return []


# ===================================================================
# Hub lifecycle commands
# ===================================================================

@app.command()
def start() -> None:
    """Start the Squareberg hub server (foreground)."""
    if _hub_is_running():
        console.print("[yellow]Hub is already running[/yellow] at " + _HUB_URL)
        raise typer.Exit(0)

    console.print(f"Starting Squareberg Hub on [bold]{_config.host}:{_config.port}[/bold] ...")
    import uvicorn
    uvicorn.run(
        "hub.main:app",
        host=_config.host,
        port=_config.port,
        log_level=_config.log_level.lower(),
    )


@app.command()
def stop() -> None:
    """Stop the Squareberg hub server."""
    # Try graceful shutdown via process signal
    pids = _find_hub_pids()
    if not pids:
        console.print("[yellow]Hub does not appear to be running.[/yellow]")
        raise typer.Exit(0)

    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            console.print(f"Sent SIGTERM to hub process [bold]{pid}[/bold].")
        except ProcessLookupError:
            console.print(f"[yellow]Process {pid} already exited.[/yellow]")
        except PermissionError:
            console.print(f"[red]Permission denied sending signal to {pid}.[/red]")

    console.print("[green]Hub stop signal sent.[/green]")


@app.command()
def status() -> None:
    """Show hub status and list registered apps."""
    running = _hub_is_running()

    if running:
        console.print(f"Hub: [green]running[/green] at {_HUB_URL}")
        apps_data = _api_get("/registry")
    else:
        console.print("Hub: [red]stopped[/red]")
        reg = _offline_registry()
        apps_data = [info.to_dict() for info in reg.list()]

    if not apps_data:
        console.print("  No apps registered.")
        return

    table = Table(title="Registered Apps")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Description")

    for a in apps_data:
        status_style = {
            "running": "[green]running[/green]",
            "stopped": "[dim]stopped[/dim]",
            "error": "[red]error[/red]",
        }.get(a.get("status", ""), a.get("status", ""))
        table.add_row(a["name"], a.get("version", ""), status_style, a.get("description", ""))

    console.print(table)


# ===================================================================
# App management commands
# ===================================================================

@app_cmd.command("list")
def app_list() -> None:
    """List installed apps."""
    running = _hub_is_running()

    if running:
        apps_data = _api_get("/registry")
    else:
        reg = _offline_registry()
        apps_data = [info.to_dict() for info in reg.list()]

    if not apps_data:
        console.print("No apps installed.")
        return

    table = Table(title="Installed Apps")
    table.add_column("Name", style="bold")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Description")

    for a in apps_data:
        status_style = {
            "running": "[green]running[/green]",
            "stopped": "[dim]stopped[/dim]",
            "error": "[red]error[/red]",
        }.get(a.get("status", ""), a.get("status", ""))
        table.add_row(a["name"], a.get("version", ""), status_style, a.get("description", ""))

    console.print(table)


@app_cmd.command("add")
def app_add(
    source: str = typer.Argument(help="GitHub URL or local path to install from."),
    as_name: Optional[str] = typer.Option(None, "--as", help="Custom folder name for the app."),
) -> None:
    """Install an app from a GitHub URL or local path."""
    apps_dir = get_apps_dir()

    is_git = "github.com" in source or source.startswith("https://") or source.startswith("git@")

    # Step 1: Acquire source into a temporary name, then rename after reading manifest
    if is_git:
        # Clone to a temporary directory first to read the manifest
        tmp_dir = apps_dir / "__installing__"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        console.print(f"Cloning [bold]{source}[/bold] ...")
        _run_cmd(["git", "clone", source, str(tmp_dir)], label=f"git clone {source}")
    else:
        src_path = Path(source).resolve()
        if not src_path.is_dir():
            console.print(f"[red]Source directory not found:[/red] {source}")
            raise typer.Exit(1)
        tmp_dir = apps_dir / "__installing__"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        console.print(f"Copying [bold]{src_path}[/bold] ...")
        shutil.copytree(src_path, tmp_dir)

    # Step 2: Validate manifest and determine app name
    manifest = _read_manifest(tmp_dir)
    app_name = as_name or manifest.get("app", {}).get("name", tmp_dir.name)

    # Move to final location
    final_dir = apps_dir / app_name
    if final_dir.exists():
        shutil.rmtree(tmp_dir)
        console.print(f"[red]App directory already exists:[/red] {final_dir}")
        console.print("Use --as to specify a different name, or remove the existing app first.")
        raise typer.Exit(1)

    tmp_dir.rename(final_dir)
    console.print(f"Installed to [bold]{final_dir}[/bold]")

    # Step 3: Create venv and install backend deps
    _install_backend(final_dir)

    # Step 4: Build active frontends
    _build_active_frontends(final_dir, manifest)

    # Notify the running hub so it picks up the new app immediately.
    if _hub_is_running():
        try:
            _api_post("/registry/scan")
        except SystemExit:
            pass

    console.print(f"[green]App '{app_name}' installed successfully.[/green]")


@app_cmd.command("remove")
def app_remove(
    name: str = typer.Argument(help="Name of the app to remove."),
) -> None:
    """Remove an installed app."""
    # If hub is running, stop the app first
    if _hub_is_running():
        try:
            _api_post(f"/registry/{name}/stop")
            console.print(f"Stopped app '{name}'.")
        except SystemExit:
            pass  # app might not be running, that is fine

    app_dir = get_apps_dir() / name
    if not app_dir.is_dir():
        console.print(f"[red]App directory not found:[/red] {app_dir}")
        raise typer.Exit(1)

    shutil.rmtree(app_dir)

    # Remove from the hub's in-memory registry if it is running.
    if _hub_is_running():
        try:
            _api_delete(f"/registry/{name}")
        except SystemExit:
            pass  # hub may not know about this app; that is fine

    console.print(f"[green]Removed app '{name}'.[/green]")


@app_cmd.command("start")
def app_start(
    name: str = typer.Argument(help="Name of the app to start."),
) -> None:
    """Start a specific app (requires hub to be running)."""
    if not _hub_is_running():
        console.print("[red]Hub is not running.[/red] Start it first with: sqb start")
        raise typer.Exit(1)

    console.print(f"Starting app [bold]{name}[/bold] ...")
    result = _api_post(f"/registry/{name}/start")
    console.print(f"[green]{result.get('message', 'OK')}[/green]")


@app_cmd.command("stop")
def app_stop(
    name: str = typer.Argument(help="Name of the app to stop."),
) -> None:
    """Stop a specific app (requires hub to be running)."""
    if not _hub_is_running():
        console.print("[red]Hub is not running.[/red]")
        raise typer.Exit(1)

    console.print(f"Stopping app [bold]{name}[/bold] ...")
    result = _api_post(f"/registry/{name}/stop")
    console.print(f"[green]{result.get('message', 'OK')}[/green]")


@app_cmd.command("logs")
def app_logs(
    name: str = typer.Argument(help="Name of the app whose logs to tail."),
    lines: int = typer.Option(50, "-n", "--lines", help="Number of lines to show."),
    follow: bool = typer.Option(False, "-f", "--follow", help="Follow log output."),
) -> None:
    """Tail an app's log file."""
    log_dir = get_log_dir(_config)
    log_file = log_dir / f"{name}.log"

    if not log_file.is_file():
        console.print(f"[yellow]No log file found for '{name}'.[/yellow]")
        console.print(f"  Expected: {log_file}")
        raise typer.Exit(1)

    if follow:
        cmd = ["tail", "-f", "-n", str(lines), str(log_file)]
    else:
        cmd = ["tail", "-n", str(lines), str(log_file)]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


@app_cmd.command("update")
def app_update(
    name: str = typer.Argument(help="Name of the app to update."),
) -> None:
    """Update a git-sourced app (git pull + rebuild)."""
    app_dir = get_apps_dir() / name
    if not app_dir.is_dir():
        console.print(f"[red]App directory not found:[/red] {app_dir}")
        raise typer.Exit(1)

    git_dir = app_dir / ".git"
    if not git_dir.is_dir():
        console.print(f"[red]App '{name}' is not a git repository.[/red] Cannot update.")
        raise typer.Exit(1)

    console.print(f"Updating [bold]{name}[/bold] ...")
    _run_cmd(["git", "pull"], cwd=app_dir, label="git pull")

    # Rebuild backend deps
    _install_backend(app_dir)

    # Rebuild active frontends
    manifest = _read_manifest(app_dir)
    _build_active_frontends(app_dir, manifest)

    console.print(f"[green]App '{name}' updated successfully.[/green]")


# ===================================================================
# Frontend management commands
# ===================================================================

@frontend_cmd.command("list")
def frontend_list(
    app_name: str = typer.Argument(help="Name of the app."),
) -> None:
    """List bundled frontends for an app and which are active."""
    app_dir = get_apps_dir() / app_name

    # Also check examples directory
    if not app_dir.is_dir():
        examples_dir = get_examples_dir() / app_name
        if examples_dir.is_dir():
            app_dir = examples_dir
        else:
            console.print(f"[red]App directory not found:[/red] {app_name}")
            raise typer.Exit(1)

    manifest = _read_manifest(app_dir)
    frontend_section = manifest.get("frontend", {})
    active_list = frontend_section.get("active", [])

    # Collect all frontend entries (sub-tables of [frontend])
    frontends: list[tuple[str, dict]] = []
    for key, val in frontend_section.items():
        if isinstance(val, dict):
            frontends.append((key, val))

    if not frontends:
        console.print(f"No frontends bundled with app '{app_name}'.")
        return

    table = Table(title=f"Frontends for '{app_name}'")
    table.add_column("Name", style="bold")
    table.add_column("Display Name")
    table.add_column("Path")
    table.add_column("Active")

    for fe_name, fe_cfg in frontends:
        is_active = fe_name in active_list
        active_marker = "[green]yes[/green]" if is_active else "[dim]no[/dim]"
        table.add_row(
            fe_name,
            fe_cfg.get("display_name", ""),
            fe_cfg.get("path", f"frontend/{fe_name}"),
            active_marker,
        )

    console.print(table)


@frontend_cmd.command("switch")
def frontend_switch(
    app_name: str = typer.Argument(help="Name of the app."),
    fe_name: str = typer.Argument(help="Frontend name to activate."),
) -> None:
    """Switch an app's active frontend and rebuild it."""
    app_dir = get_apps_dir() / app_name

    if not app_dir.is_dir():
        examples_dir = get_examples_dir() / app_name
        if examples_dir.is_dir():
            app_dir = examples_dir
        else:
            console.print(f"[red]App directory not found:[/red] {app_name}")
            raise typer.Exit(1)

    manifest = _read_manifest(app_dir)
    frontend_section = manifest.get("frontend", {})

    # Verify the frontend exists in the manifest
    if fe_name not in frontend_section or not isinstance(frontend_section.get(fe_name), dict):
        available = [k for k, v in frontend_section.items() if isinstance(v, dict)]
        console.print(f"[red]Frontend '{fe_name}' not found in manifest.[/red]")
        if available:
            console.print(f"  Available: {', '.join(available)}")
        raise typer.Exit(1)

    # Update the active list
    manifest.setdefault("frontend", {})["active"] = [fe_name]
    _write_manifest(app_dir, manifest)
    console.print(f"Set active frontend to [bold]{fe_name}[/bold].")

    # Rebuild
    fe_config = frontend_section[fe_name]
    fe_path = fe_config.get("path", f"frontend/{fe_name}")
    _build_frontend(app_dir, fe_path)

    console.print(f"[green]Frontend '{fe_name}' activated and rebuilt.[/green]")
