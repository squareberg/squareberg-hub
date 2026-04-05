# Architecture

## High-Level Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────────┐ │
│  │ Dashboard │  │ App UIs  │  │ OpenAPI Introspection  │ │
│  └────┬─────┘  └────┬─────┘  └───────────┬────────────┘ │
└───────┼──────────────┼────────────────────┼─────────────┘
        │              │                    │
      fetch          fetch               fetch
        │              │                    │
┌───────▼──────────────▼────────────────────▼─────────────┐
│  Hub process (FastAPI + uvicorn)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Registry │  │ Reverse  │  │ Process  │              │
│  │          │  │ Proxy    │  │ Manager  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│       port 9100                                         │
└──────────┬───────────────┬──────────────────────────────┘
           │               │
       Unix socket     Unix socket
           │               │
    ┌──────▼──────┐  ┌─────▼──────┐
    │ App: hello  │  │ App: kanban│  ...
    │ (own venv)  │  │ (own venv) │
    │ SQLite db   │  │ SQLite db  │
    └─────────────┘  └────────────┘
```

Everything the browser touches goes through the hub on port 9100. The hub is the sole listener on a network port; apps never bind to TCP ports.

## Process Model

Each app runs as a **separate subprocess** with its own Python virtual environment. The hub spawns apps via `uvicorn` and monitors them for the lifetime of the hub process.

Key properties of this model:

- **Crash isolation** — if one app's process exits, the hub detects this and marks the app as `error`. Other apps are unaffected.
- **Dependency isolation** — each app's venv is independent. Two apps can use different versions of the same library without conflict.
- **No shared memory** — apps cannot import from each other. All inter-app communication goes through HTTP calls routed by the hub.
- **Lightweight hub** — the hub itself has minimal dependencies (FastAPI, uvicorn, httpx, typer). It does not carry the weight of every app's requirements.

The hub manages the following lifecycle states for each app:

| State | Meaning |
|-------|---------|
| `stopped` | No process running; socket file absent |
| `running` | Subprocess live; socket file present |
| `error` | Process exited unexpectedly or failed health check |

## Socket Location

Apps listen on **Unix domain sockets** rather than TCP ports, eliminating port allocation conflicts and providing slightly better loopback performance.

Socket files are created at runtime in one of two locations, checked in order:

1. `$XDG_DATA_HOME/squareberg/sockets/` — preferred; defaults to `~/.local/share/squareberg/sockets/`
2. `<project-root>/sockets/` — fallback for development; this directory is gitignored

The socket filename for an app named `hello` is `hello.sock`. The hub creates the socket directory on startup if it does not exist.

The socket mode can be controlled in `hub/config.toml`:

```toml
[hub.sockets]
mode = "xdg"   # "xdg" (default) or "local"
```

## Routing

The hub handles four categories of requests, in priority order:

### 1. API proxy: `/apps/{name}/api/*`

Requests matching this pattern are forwarded to the app's Unix socket using `httpx.AsyncClient` with a Unix socket transport. Example:

```
GET /apps/hello/api/greet?name=world
  → proxy to unix:///path/to/hello.sock → GET /api/greet?name=world
```

The hub strips the `/apps/{name}` prefix before forwarding, so the app sees a clean `/api/...` path. Query strings, request bodies, and HTTP methods are all forwarded faithfully.

### 2. Static file serving: `/apps/{name}/*`

Requests that do not match the `/api/` sub-path are served from the app's active frontend `dist/` directory. This is a standard `StaticFiles` mount with HTML mode enabled (i.e., `index.html` fallback for SPA routing).

### 3. Registry API: `/registry/*`

The hub's own REST API for listing apps, fetching metadata, starting and stopping apps, and retrieving OpenAPI specs. See [Hub API](../reference/hub-api.md).

### 4. Dashboard: `/`

The hub's own SPA served from `hub/dashboard/dist/`. Falls back to an inline placeholder page if the dashboard has not been built.

## Registry

On startup, the hub's `Registry` class scans two directories for apps:

1. `apps/` — runtime-installed apps (gitignored)
2. `examples/` — in-tree example apps for development and testing

Within each directory, every subdirectory containing a `.squareberg/manifest.toml` file is registered as an app. The manifest is parsed to extract the app name, display name, version, description, backend module, and active frontend path.

If a name collision occurs (two apps with the same `name` field), the second one is skipped and a warning is logged.

The registry is populated once at startup. Adding a new app with `sqb app add` modifies the filesystem; a hub restart is required for it to appear in the registry.

!!! note "Automatic restart on app install"
    Future versions may support hot-reload of the registry. For now, restart the hub after installing or removing apps.
