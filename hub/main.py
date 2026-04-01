"""Squareberg Hub — FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import HubConfig, get_apps_dir, get_log_dir, get_socket_dir, load_config
from .manager import ProcessManager
from .proxy import proxy_request
from .registry import Registry

logger = logging.getLogger("squareberg.hub")

# ---------------------------------------------------------------------------
# Shared state (populated during lifespan)
# ---------------------------------------------------------------------------
_config: HubConfig
_registry: Registry
_manager: ProcessManager


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _config, _registry, _manager

    # --- Startup ---
    _config = load_config()

    logging.basicConfig(
        level=getattr(logging, _config.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    socket_dir = get_socket_dir(_config)
    log_dir = get_log_dir(_config)
    apps_dir = get_apps_dir()

    _registry = Registry(apps_dir=apps_dir, socket_dir=socket_dir)
    _registry.scan()

    _manager = ProcessManager(
        registry=_registry,
        socket_dir=socket_dir,
        log_dir=log_dir,
    )

    # Mount per-app static frontends (must happen before the catch-all proxy).
    _mount_app_frontends(app, _registry)

    # Mount the hub dashboard.
    _mount_dashboard(app)

    logger.info(
        "Squareberg Hub starting on %s:%d — %d app(s) registered.",
        _config.host, _config.port, len(_registry.list()),
    )

    yield

    # --- Shutdown ---
    logger.info("Squareberg Hub shutting down...")
    await _manager.stop_all()


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Squareberg Hub",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------

@app.get("/registry")
async def list_apps():
    """List all registered apps."""
    return [info.to_dict() for info in _registry.list()]


@app.get("/registry/{name}")
async def get_app(name: str):
    """Get metadata for a single app."""
    info = _registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found.")
    return info.to_dict()


@app.get("/registry/{name}/spec")
async def get_app_spec(name: str):
    """Proxy the app's OpenAPI spec (/openapi.json) from its Unix socket."""
    info = _registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found.")
    if info.status != "running":
        raise HTTPException(
            status_code=503,
            detail=f"App '{name}' is not running. Start it first.",
        )

    socket_path = Path(info.socket_path)  # type: ignore[arg-type]
    try:
        resp = await proxy_request(
            socket_path=socket_path,
            method="GET",
            path="/openapi.json",
            headers=[],
        )
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
    except Exception as exc:
        logger.error("Failed to fetch spec for '%s': %s", name, exc)
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/registry/{name}/start")
async def start_app(name: str):
    """Start an app."""
    info = _registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found.")
    try:
        await _manager.start_app(name)
    except Exception as exc:
        logger.error("Failed to start app '%s': %s", name, exc)
        raise HTTPException(status_code=500, detail=str(exc))
    return {"status": "ok", "app": name, "message": f"App '{name}' started."}


@app.post("/registry/{name}/stop")
async def stop_app(name: str):
    """Stop an app."""
    info = _registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found.")
    try:
        await _manager.stop_app(name)
    except Exception as exc:
        logger.error("Failed to stop app '%s': %s", name, exc)
        raise HTTPException(status_code=500, detail=str(exc))
    return {"status": "ok", "app": name, "message": f"App '{name}' stopped."}


# ---------------------------------------------------------------------------
# Reverse proxy catch-all: /apps/{name}/api/{path}
# ---------------------------------------------------------------------------

@app.api_route(
    "/apps/{name}/api/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def proxy_to_app(name: str, path: str, request: Request):
    """Proxy API requests to the appropriate app's Unix socket."""
    info = _registry.get(name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"App '{name}' not found.")
    if info.status != "running":
        raise HTTPException(
            status_code=503,
            detail=f"App '{name}' is not running. Start it first via POST /registry/{name}/start",
        )

    socket_path = Path(info.socket_path)  # type: ignore[arg-type]
    if not socket_path.exists():
        raise HTTPException(
            status_code=503, detail=f"Socket for app '{name}' not found."
        )

    # Build the upstream path: /api/{path}
    upstream_path = f"/api/{path}" if path else "/api"
    body = await request.body()
    headers = list(request.headers.items())
    query_string = str(request.url.query) if request.url.query else ""

    try:
        resp = await proxy_request(
            socket_path=socket_path,
            method=request.method,
            path=upstream_path,
            headers=headers,
            body=body or None,
            query_string=query_string,
        )
    except Exception as exc:
        logger.error("Proxy error for '%s': %s", name, exc)
        raise HTTPException(status_code=502, detail=f"Proxy error: {exc}")

    # Build the response, forwarding status and headers.
    excluded_headers = {"content-encoding", "content-length", "transfer-encoding"}
    response_headers = {
        k: v
        for k, v in resp.headers.items()
        if k.lower() not in excluded_headers
    }

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=response_headers,
        media_type=resp.headers.get("content-type"),
    )


# ---------------------------------------------------------------------------
# Static file mounting helpers
# ---------------------------------------------------------------------------

_DASHBOARD_PLACEHOLDER = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Squareberg Hub</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; background: #f5f5f5; color: #333;
    }
    .card {
      background: #fff; border-radius: 12px; padding: 3rem 2.5rem;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08); text-align: center;
      max-width: 420px;
    }
    h1 { font-size: 1.6rem; margin-bottom: 0.5rem; }
    p  { color: #666; margin-bottom: 1.5rem; }
    a  {
      display: inline-block; padding: 0.6rem 1.4rem;
      background: #4f46e5; color: #fff; border-radius: 8px;
      text-decoration: none; font-weight: 500;
    }
    a:hover { background: #4338ca; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Squareberg Hub</h1>
    <p>Dashboard coming soon.</p>
    <a href="/registry">View Registry</a>
  </div>
</body>
</html>
"""


def _mount_app_frontends(fastapi_app: FastAPI, registry: Registry) -> None:
    """Mount static-file directories for each app that has a built frontend."""
    for info in registry.list():
        if info.frontend_dist_path and Path(info.frontend_dist_path).is_dir():
            mount_path = f"/apps/{info.name}"
            fastapi_app.mount(
                mount_path,
                StaticFiles(directory=info.frontend_dist_path, html=True),
                name=f"frontend-{info.name}",
            )
            logger.info(
                "Mounted frontend for '%s' at %s → %s",
                info.name, mount_path, info.frontend_dist_path,
            )


def _mount_dashboard(fastapi_app: FastAPI) -> None:
    """Mount the hub dashboard — built SPA if available, else a placeholder."""
    dashboard_dist = Path(__file__).resolve().parent / "dashboard" / "dist"

    if dashboard_dist.is_dir():
        fastapi_app.mount(
            "/",
            StaticFiles(directory=str(dashboard_dist), html=True),
            name="dashboard",
        )
        logger.info("Mounted dashboard from %s", dashboard_dist)
    else:
        # Serve an inline placeholder page.
        @fastapi_app.get("/", response_class=HTMLResponse)
        async def dashboard_placeholder():
            return _DASHBOARD_PLACEHOLDER
