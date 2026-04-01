"""Process manager — spawns, monitors, and stops app subprocesses."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from pathlib import Path
from typing import Optional

from .registry import Registry

logger = logging.getLogger("squareberg.manager")

# How long to wait for a socket file to appear after spawning a process.
_SOCKET_POLL_INTERVAL = 0.15  # seconds
_SOCKET_POLL_TIMEOUT = 10.0  # seconds

# Graceful shutdown timeout before SIGKILL.
_STOP_TIMEOUT = 5.0  # seconds


class ProcessManager:
    """Manage app subprocesses — start, stop, health-check."""

    def __init__(self, registry: Registry, socket_dir: Path, log_dir: Path) -> None:
        self._registry = registry
        self._socket_dir = socket_dir
        self._log_dir = log_dir
        self._processes: dict[str, asyncio.subprocess.Process] = {}

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    async def start_app(self, name: str) -> None:
        """Start an app by name.

        Resolves the app's venv Python, spawns uvicorn on a Unix socket,
        and waits for the socket file to appear.
        """
        if name in self._processes:
            proc = self._processes[name]
            if proc.returncode is None:
                logger.info("App '%s' is already running (pid %d).", name, proc.pid)
                return

        info = self._registry.get(name)
        if info is None:
            raise ValueError(f"Unknown app: {name}")

        app_dir = Path(info.app_dir)  # type: ignore[arg-type]
        python = self._resolve_python(app_dir)
        if python is None:
            raise FileNotFoundError(
                f"No Python venv found for app '{name}'. "
                f"Looked in {app_dir / '.venv'} and {app_dir / 'backend' / '.venv'}."
            )

        socket_path = Path(info.socket_path)  # type: ignore[arg-type]

        # Remove stale socket if present.
        if socket_path.exists():
            socket_path.unlink()

        module = info.backend_module or "app:app"
        backend_dir = app_dir / "backend"
        if not backend_dir.is_dir():
            backend_dir = app_dir  # fallback: app root is the backend

        cmd = [
            str(python), "-m", "uvicorn",
            module,
            "--uds", str(socket_path),
            "--app-dir", str(backend_dir),
            "--log-level", "info",
        ]

        log_file_path = self._log_dir / f"{name}.log"
        log_fh = open(log_file_path, "ab")

        logger.info("Starting app '%s': %s", name, " ".join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=log_fh,
            stderr=log_fh,
            cwd=str(backend_dir),
        )
        self._processes[name] = proc

        # Wait for the socket file to appear.
        elapsed = 0.0
        while elapsed < _SOCKET_POLL_TIMEOUT:
            if proc.returncode is not None:
                self._registry.set_status(name, "error")
                raise RuntimeError(
                    f"App '{name}' exited immediately with code {proc.returncode}. "
                    f"Check logs at {log_file_path}"
                )
            if socket_path.exists():
                break
            await asyncio.sleep(_SOCKET_POLL_INTERVAL)
            elapsed += _SOCKET_POLL_INTERVAL
        else:
            # Timed out — kill the process.
            await self._kill(proc)
            self._registry.set_status(name, "error")
            raise TimeoutError(
                f"App '{name}' did not create socket within {_SOCKET_POLL_TIMEOUT}s. "
                f"Check logs at {log_file_path}"
            )

        self._registry.set_status(name, "running")
        logger.info("App '%s' is running (pid %d).", name, proc.pid)

    # ------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------

    async def stop_app(self, name: str) -> None:
        """Stop a running app gracefully, escalating to SIGKILL if needed."""
        proc = self._processes.pop(name, None)
        if proc is None or proc.returncode is not None:
            self._registry.set_status(name, "stopped")
            self._cleanup_socket(name)
            return

        logger.info("Stopping app '%s' (pid %d)...", name, proc.pid)

        # Send SIGTERM.
        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            pass

        try:
            await asyncio.wait_for(proc.wait(), timeout=_STOP_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning("App '%s' did not exit in time; sending SIGKILL.", name)
            await self._kill(proc)

        self._cleanup_socket(name)
        self._registry.set_status(name, "stopped")
        logger.info("App '%s' stopped.", name)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self, name: str) -> bool:
        """Probe an app's /api/health endpoint via its Unix socket."""
        info = self._registry.get(name)
        if info is None or info.socket_path is None:
            return False

        socket_path = Path(info.socket_path)
        if not socket_path.exists():
            return False

        try:
            import httpx

            transport = httpx.AsyncHTTPTransport(uds=str(socket_path))
            async with httpx.AsyncClient(transport=transport) as client:
                resp = await client.get("http://localhost/api/health", timeout=3.0)
                return resp.status_code == 200
        except Exception:
            logger.debug("Health check failed for '%s'.", name, exc_info=True)
            return False

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def start_all(self) -> None:
        """Start all registered apps."""
        for info in self._registry.list():
            try:
                await self.start_app(info.name)
            except Exception:
                logger.error("Failed to start app '%s'.", info.name, exc_info=True)

    async def stop_all(self) -> None:
        """Stop all running apps."""
        names = list(self._processes.keys())
        for name in names:
            try:
                await self.stop_app(name)
            except Exception:
                logger.error("Failed to stop app '%s'.", name, exc_info=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_python(app_dir: Path) -> Path | None:
        """Find the venv Python binary for an app.

        Checks two locations:
          1. <app_dir>/.venv/bin/python
          2. <app_dir>/backend/.venv/bin/python
        """
        for candidate in (
            app_dir / ".venv" / "bin" / "python",
            app_dir / "backend" / ".venv" / "bin" / "python",
        ):
            if candidate.is_file():
                return candidate
        return None

    @staticmethod
    async def _kill(proc: asyncio.subprocess.Process) -> None:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        await proc.wait()

    def _cleanup_socket(self, name: str) -> None:
        info = self._registry.get(name)
        if info and info.socket_path:
            sock = Path(info.socket_path)
            if sock.exists():
                try:
                    sock.unlink()
                except OSError:
                    pass
