# Squareberg — Hub Design Blueprint

## Overview

Squareberg is a local application hub that aggregates personal productivity tools ("apps") behind a unified API gateway. Each app is a standalone FastAPI backend with its own virtual environment, communicating with the hub over Unix domain sockets. Frontends are decoupled from backends: each app ships its own client-side SPA(s), and the hub provides a dashboard launcher plus a generic OpenAPI introspection layer.

Each app is developed and distributed as an independent repository. The hub's `apps/` directory is a runtime-only location (gitignored) where apps are installed via the CLI.

The project targets macOS as the primary platform, with Linux support (select distros) planned as a secondary goal. Windows is explicitly out of scope.

The CLI is available as both `squareberg` and `sqb`.

---

## Architecture

### High-level diagram

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
    │ App: papers │  │ App: kanban│  ...
    │ (own venv)  │  │ (own venv) │
    │ SQLite db   │  │ SQLite db  │
    └─────────────┘  └────────────┘
```

### Process model

Each app runs as a **separate process** with its own Python virtual environment, managed by the hub. Apps listen on **Unix domain sockets** rather than TCP ports, which eliminates port allocation conflicts and provides slightly better loopback performance.

The hub itself is a thin process with minimal dependencies. Its responsibilities:

1. **Registry** — track which apps are installed, their metadata, health status, and OpenAPI specs.
2. **Reverse proxy** — route requests from `/apps/{name}/*` to the corresponding Unix socket.
3. **Process manager** — spawn, monitor, and restart app subprocesses.
4. **Static file server** — serve the dashboard SPA and per-app frontend bundles.

Apps are not allowed to import from each other. All inter-app communication goes through HTTP calls to the hub's API. This constraint ensures any app can be moved, replaced, or restarted independently.

### Socket location

Unix domain sockets are created at runtime in one of two locations, checked in order:

1. `$XDG_DATA_HOME/squareberg/sockets/` (preferred; defaults to `~/.local/share/squareberg/sockets/`)
2. `<hub-root>/sockets/` (fallback for development; this directory is gitignored and created dynamically)

The hub creates the socket directory on startup if it does not exist.

---

## App structure

Apps are developed and distributed as **independent repositories**. At runtime, they are installed into the hub's `apps/` directory (gitignored, not versioned). A hello-world app lives in-tree under `examples/hello/` for bootstrapping and testing.

### Repository layout

```
my-app-repo/
├── .squareberg/
│   └── manifest.toml        # app metadata, backend entry, frontend registry
├── backend/
│   ├── pyproject.toml        # Python dependencies
│   ├── app.py                # FastAPI entry point
│   ├── models.py
│   ├── db.py
│   └── ...
├── frontend/
│   ├── default/              # primary frontend
│   │   ├── src/
│   │   ├── package.json
│   │   └── vite.config.js
│   └── minimal/              # alternate frontend (may be inactive)
│       └── ...
├── data/                     # runtime data directory (gitignored)
└── README.md
```

### App manifest

Each app declares itself via `.squareberg/manifest.toml`:

```toml
[app]
name = "papers"
display_name = "Papers"
description = "Research paper and document library"
version = "0.1.0"

[backend]
module = "app:app"               # uvicorn target, relative to backend/

[frontend]
active = ["default"]             # which frontends are built and served by the hub

[frontend.default]
path = "frontend/default"
display_name = "Default"

[frontend.minimal]
path = "frontend/minimal"
display_name = "Minimal"
```

The `active` list determines which frontends the hub builds and serves. Updates to an app may break some frontends; only those listed in `active` are guaranteed to work with the current backend version. The CLI provides commands to switch between bundled frontends.

### API specification

The OpenAPI spec is **generated at runtime by FastAPI** (`/openapi.json`). There is no need to maintain a separate spec file in the repository. When the hub starts an app, it fetches the spec from the running instance to populate the registry and the introspection UI.

### App entry point contract

Every app must expose a standard FastAPI application object:

```python
# backend/app.py
from fastapi import FastAPI

app = FastAPI(
    title="Papers",
    version="0.1.0",
    root_path="/apps/papers",   # must match hub mount point
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/search")
async def search(q: str):
    ...
```

The `root_path` setting ensures OpenAPI spec URLs and documentation paths are correct when the app is served behind the hub's reverse proxy.

---

## Hub internals

### Reverse proxy

The hub proxies requests using `httpx.AsyncClient` configured with Unix socket transport. Routing logic:

```
GET  /apps/papers/api/search?q=foo
  → proxy to unix:///path/to/papers.sock → GET /api/search?q=foo

GET  /apps/papers/*
  → serve static files from papers' active frontend dist/
```

Route priority:
1. `/apps/{name}/api/*` — proxied to app process
2. `/apps/{name}/*` — served from app's active frontend bundle
3. `/registry` — hub's own registry endpoint
4. `/` — hub dashboard

### Process manager

The hub manages app lifecycles:

- **Start**: spawn `<app>/.venv/bin/uvicorn <module> --uds <socket_path>` as a subprocess, with `cwd` set to `<app>/backend/`.
- **Health check**: periodic probe to `GET /api/health` on each app socket.
- **Restart**: if an app process exits or fails health checks, restart it with exponential backoff (max 3 retries, then mark as failed).
- **Stop**: send SIGTERM, wait for graceful shutdown, SIGKILL after timeout.
- **Logs**: capture stdout/stderr per app to `$XDG_DATA_HOME/squareberg/logs/{app_name}.log`.

### Registry API

```
GET  /registry              → list all apps with status
GET  /registry/{name}       → app metadata, status, health
GET  /registry/{name}/spec  → app's OpenAPI JSON spec (fetched from app)
POST /registry/{name}/start → start an app
POST /registry/{name}/stop  → stop an app
```

### Hub configuration

Hub-level settings live in `hub/config.toml`:

```toml
[hub]
host = "127.0.0.1"
port = 9100

[hub.sockets]
# "xdg" or "local"; determines socket directory strategy
mode = "xdg"

[hub.logging]
level = "info"
dir = ""  # empty = $XDG_DATA_HOME/squareberg/logs/
```

---

## Data storage

### Default: SQLite (per-app)

Each app manages its own SQLite database(s) in its `data/` directory. This provides:

- Zero configuration — no external database process.
- Per-app isolation — apps cannot accidentally corrupt each other's data.
- Simple backups — copy the file.
- Excellent Python support via the standard library or `aiosqlite` for async.

Recommended libraries: `aiosqlite` for async access, `sqlite-utils` for rapid prototyping.

### Optional: TinyDB (per-app, document/NoSQL)

For apps that need a document-oriented or NoSQL data model (flexible schemas, nested JSON structures, rapid prototyping without migrations), **TinyDB** is included as a supported option:

- Pure Python, zero dependencies, stores data as JSON files.
- Simple document-oriented API: insert, search, update with query expressions.
- No server process, file-based like SQLite.
- Well-suited for small-to-medium datasets (bookmarks, tags, settings, metadata).

```python
from tinydb import TinyDB, Query
db = TinyDB("data/bookmarks.json")
db.insert({"url": "https://...", "tags": ["ml", "transformers"]})
Bookmark = Query()
db.search(Bookmark.tags.any(["ml"]))
```

TinyDB is intentionally limited in scale. If an app outgrows it (>100K documents, complex queries, concurrent writes), it should migrate to SQLite with JSON columns or a dedicated document store.

### Future consideration: embedded document database

If a stronger NoSQL option is needed in the future, candidates to evaluate:

- **UnQLite** (via `unqlite-python`) — embedded key/value and document store, C-based, no server, more performant than TinyDB.
- **MongoDB with mongita** — MongoDB API on top of local file storage, no server needed. Young project, worth watching.
- **SQLite JSON1 extension** — SQLite itself supports JSON columns with indexing and querying, which can serve as a "document store lite" without adding any dependency.

The recommendation is to start with SQLite (relational) and TinyDB (document/NoSQL) as the two built-in options, and revisit if concrete performance or feature gaps emerge.

---

## Frontend architecture

### Stack

- **Preact** — 3KB React-compatible framework for building interactive UIs.
- **Tailwind CSS** — utility-first CSS framework.
- **daisyUI** — component class library on top of Tailwind (buttons, cards, modals, etc.).
- **Vite** — build tool for development server and production bundling.

### Delivery model

All frontends are **purely client-side SPAs**. No Node server is involved at runtime. Vite is used at dev/build time to compile JSX and Tailwind; the output is plain static files (HTML, JS, CSS) served by the Python backend.

### Per-app frontends

Each app can bundle **multiple frontends** under `frontend/` (e.g. `frontend/default/`, `frontend/minimal/`). The manifest's `[frontend] active` list determines which are built and served. The hub serves the first active frontend's static files at `/apps/{name}/*`.

Apps are not required to ship a frontend. An app without one is still fully functional via the introspection UI and direct API calls.

### Frontend switching

Users can switch an app's active frontend via the CLI:

```bash
sqb frontend list papers          # show bundled frontends and which is active
sqb frontend switch papers minimal   # activate "minimal", rebuild, restart serving
```

This updates the app's manifest and triggers a frontend rebuild. Since app updates may break some frontends, only explicitly activated frontends are guaranteed to work.

### Hub dashboard

The hub serves its own dashboard SPA at `/`. This is the main launcher UI — a grid of cards ("squares") representing installed apps, showing:

- App name, description, version
- Status (running / stopped / error)
- Links to the app's UI and its API spec
- Start/stop controls

The dashboard reads from `GET /registry` to populate itself.

### OpenAPI introspection UI

Available at `/inspect/{name}` (or a similar path), this is a generic API browser that:

- Fetches an app's OpenAPI spec from the registry.
- Renders a browsable, interactive view of all endpoints.
- Allows sending test requests directly from the browser.

This is a **developer/meta tool**, separate from the app's own UI. It is also the interface that AI agents would use to discover and interact with app APIs.

FastAPI bundles Swagger UI and ReDoc by default. The introspection layer can start as a styled wrapper around these, and evolve into a custom implementation if needed.

---

## Shared services

Services the hub may provide to all apps. These are optional and should be added incrementally, not upfront.

### Logging (priority: high)

Centralized log aggregation. The hub captures each app's stdout/stderr and writes to per-app log files. A future dashboard panel could display logs in real-time via WebSocket.

### Keychain integration (priority: medium)

For apps that need to store secrets (API keys, tokens), the hub provides a thin wrapper around the `keyring` Python library, which abstracts macOS Keychain and Linux `libsecret`:

```python
import keyring
keyring.set_password("squareberg.papers", "crossref_api_key", "...")
keyring.get_password("squareberg.papers", "crossref_api_key")
```

Apps call the hub's secrets API rather than accessing the keychain directly, so the hub can enforce namespacing and audit access.

### Analytics / monitoring (priority: low)

Request counts, latency histograms, error rates per app. Can be implemented as a simple middleware in the hub's reverse proxy that logs request metadata, queried via a dashboard panel.

### Inter-app communication (priority: low)

Apps should not import from each other, but they may need to exchange data. The prescribed pattern is HTTP calls through the hub (e.g., the kanban app fetches paper metadata from the papers app via `GET /apps/papers/api/papers/{id}`). No additional IPC mechanism is planned initially.

---

## CLI

The CLI is available as both `squareberg` and `sqb`. Implemented with `typer`, it talks to the hub's API when the hub is running, or manages processes directly when it isn't.

```bash
# Hub lifecycle
sqb start                            # start hub + all enabled apps
sqb stop                             # stop everything
sqb status                           # hub and app status summary

# App management
sqb app add <github-url-or-path>     # clone/copy into apps/, create venv, install deps, build frontend
sqb app add <url> --as my-papers     # install with custom folder name to avoid collisions
sqb app remove <name>                # stop app, remove from apps/
sqb app list                         # list installed apps
sqb app start <name>                 # start a specific app
sqb app stop <name>                  # stop a specific app
sqb app logs <name>                  # tail app logs
sqb app update <name>               # git pull + rebuild (for git-sourced apps)

# Frontend management
sqb frontend list <app>              # list bundled frontends and which are active
sqb frontend switch <app> <name>     # activate a different frontend, rebuild
```

### App installation process

When `sqb app add` is invoked:

1. **Acquire source**: clone the Git repository or copy the local directory into `apps/{name}/` (or `apps/{custom-name}/` if `--as` is used).
2. **Validate manifest**: read `.squareberg/manifest.toml`, verify required fields.
3. **Create virtual environment**: `python -m venv apps/{name}/.venv` within the app directory.
4. **Install Python dependencies**: `apps/{name}/.venv/bin/pip install -r backend/pyproject.toml` (or equivalent).
5. **Build active frontend(s)**: `cd frontend/{active_frontend} && npm install && npm run build` for each active frontend.
6. **Register in hub**: add the app to the hub's internal registry so it appears in the dashboard and can be started.

---

## Project layout

```
squareberg/                      # hub repository
├── blueprints/                  # design docs (this file)
├── hub/
│   ├── pyproject.toml           # hub dependencies (fastapi, uvicorn, httpx, typer, etc.)
│   ├── .venv/                   # hub virtual environment (gitignored)
│   ├── main.py                  # FastAPI app, reverse proxy, registry
│   ├── proxy.py                 # httpx-based Unix socket proxy
│   ├── manager.py               # process lifecycle manager
│   ├── registry.py              # app registry and metadata
│   ├── config.py                # configuration loading
│   ├── cli.py                   # CLI entry point (sqb / squareberg)
│   └── dashboard/
│       ├── src/                 # Preact source for hub dashboard
│       ├── dist/                # built static files (gitignored)
│       ├── package.json
│       └── vite.config.js
├── examples/
│   └── hello/                   # hello-world app (in-tree, for testing)
│       ├── .squareberg/
│       │   └── manifest.toml
│       ├── backend/
│       │   ├── pyproject.toml
│       │   └── app.py
│       └── frontend/
│           └── default/
│               ├── src/
│               ├── package.json
│               └── vite.config.js
├── apps/                        # installed apps at runtime (gitignored)
├── sockets/                     # Unix socket files, dev fallback (gitignored)
├── .gitignore
└── README.md
```

---

## Implementation sequence

1. **Hub skeleton** — FastAPI app on port 9100, config loading, socket directory setup, registry endpoint.
2. **Process manager** — spawn app subprocess on Unix socket, health check, graceful shutdown.
3. **Reverse proxy** — route `/apps/{name}/api/*` to app sockets via httpx.
4. **Hello-world app** — minimal manifest + backend + frontend to validate the full install → start → proxy → serve pipeline end-to-end.
5. **CLI (core)** — `sqb start/stop/status`, `sqb app add/remove/list/start/stop`.
6. **Dashboard** — Preact + daisyUI SPA showing app grid from registry, start/stop controls.
7. **Static file serving** — serve per-app active frontend at `/apps/{name}/*`.
8. **Frontend switching** — `sqb frontend list/switch`, rebuild logic.
9. **OpenAPI introspection** — generic API browser reading specs from registry.
10. **Papers app** — first real app, in its own repository.
11. **Keychain integration** — secrets API wrapping the `keyring` library.
12. **Second app** — validate the architecture with a different use case (kanban, bookmarks, or notes).
