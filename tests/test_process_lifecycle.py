"""Tests for the process manager with the real hello app.

These tests spawn actual uvicorn subprocesses and require the hello app
venv to be set up at examples/hello/.venv/.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest

from hub.manager import ProcessManager
from hub.proxy import proxy_request
from hub.registry import Registry

# Path to the project root (parent of hub/ and examples/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_HELLO_VENV = _PROJECT_ROOT / "examples" / "hello" / ".venv" / "bin" / "python"

pytestmark = [
    pytest.mark.skipif(
        not _HELLO_VENV.exists(),
        reason="Hello app venv not set up",
    ),
]


# -----------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------


@pytest.fixture()
def short_tmp() -> Path:
    """A short-path temp directory (Unix socket paths are limited to ~104 chars)."""
    d = Path(tempfile.mkdtemp(prefix="sqb-", dir="/tmp"))
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture()
def socket_dir(short_tmp: Path) -> Path:
    """Temporary directory for Unix sockets."""
    d = short_tmp / "s"
    d.mkdir()
    return d


@pytest.fixture()
def log_dir(short_tmp: Path) -> Path:
    """Temporary directory for log files."""
    d = short_tmp / "l"
    d.mkdir()
    return d


@pytest.fixture()
def registry(socket_dir: Path) -> Registry:
    """A Registry pointing at the examples directory."""
    examples_dir = _PROJECT_ROOT / "examples"
    reg = Registry(apps_dir=examples_dir, socket_dir=socket_dir)
    reg.scan()
    return reg


@pytest.fixture()
def manager(registry: Registry, socket_dir: Path, log_dir: Path) -> ProcessManager:
    """A ProcessManager wired to the test registry."""
    return ProcessManager(
        registry=registry,
        socket_dir=socket_dir,
        log_dir=log_dir,
    )


# -----------------------------------------------------------------
# Tests
# -----------------------------------------------------------------


@pytest.mark.asyncio

async def test_start_and_health_check(manager: ProcessManager, registry: Registry):
    """Start the hello app, verify health check passes, then stop it."""
    try:
        await manager.start_app("hello")
        info = registry.get("hello")
        assert info is not None
        assert info.status == "running"

        healthy = await manager.health_check("hello")
        assert healthy is True
    finally:
        await manager.stop_app("hello")


@pytest.mark.asyncio

async def test_stop_cleans_socket(
    manager: ProcessManager, registry: Registry, socket_dir: Path
):
    """Start the app, verify socket exists, stop it, verify socket is removed."""
    try:
        await manager.start_app("hello")
        info = registry.get("hello")
        assert info is not None
        socket_path = Path(info.socket_path)
        assert socket_path.exists(), "Socket file should exist while app is running"
    finally:
        await manager.stop_app("hello")

    assert not socket_path.exists(), "Socket file should be removed after stop"


@pytest.mark.asyncio

async def test_start_already_running(manager: ProcessManager):
    """Starting an already-running app should be idempotent (no error)."""
    try:
        await manager.start_app("hello")
        # Second start should not raise
        await manager.start_app("hello")
    finally:
        await manager.stop_app("hello")


@pytest.mark.asyncio

async def test_proxy_through_socket(
    manager: ProcessManager, registry: Registry
):
    """Start the app, proxy a GET /api/hello, verify the response body."""
    try:
        await manager.start_app("hello")
        info = registry.get("hello")
        assert info is not None

        socket_path = Path(info.socket_path)
        resp = await proxy_request(
            socket_path=socket_path,
            method="GET",
            path="/api/hello",
            headers=[],
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "Hello from Squareberg!" in body.get("message", "")
    finally:
        await manager.stop_app("hello")
