# Squareberg Hub — Overview for AI Agents

This document provides context for AI agents working on or with the Squareberg project. Read this first when starting a new session.

## What is Squareberg?

Squareberg is a **local application hub** — a FastAPI-based gateway that aggregates personal productivity tools ("apps") behind a single API. Each app is an independent FastAPI backend running in its own process and virtual environment, communicating with the hub over Unix domain sockets. Frontends are decoupled: each app ships its own client-side SPA(s), served as static files by the hub.

The project targets macOS (primary) and Linux. Windows is out of scope.

## Repository structure

```
squareberg/
├── hub/                        # Hub backend (Python, FastAPI)
│   ├── main.py                 # FastAPI app: lifespan, registry API, reverse proxy, static serving
│   ├── config.py               # HubConfig dataclass, TOML loading, directory resolution (XDG)
│   ├── registry.py             # AppInfo model + Registry class (scans apps/ for manifests)
│   ├── manager.py              # ProcessManager: spawn/stop app subprocesses on Unix sockets
│   ├── proxy.py                # httpx-based reverse proxy to Unix sockets
│   ├── cli.py                  # Typer CLI (sqb/squareberg), app management, frontend switching
│   ├── explorer.html           # Self-contained dark-themed API explorer (vanilla JS)
│   ├── config.toml             # Default hub config (host, port, socket mode, logging)
│   └── dashboard/              # Hub dashboard SPA source (Preact + daisyUI + Tailwind v4 + Vite)
│       ├── src/app.jsx         # Main dashboard component (fetches /registry, renders grid)
│       ├── src/components/     # AppCard.jsx
│       └── dist/               # Built dashboard (gitignored, must run npm run build)
├── examples/
│   └── hello/                  # In-tree hello-world app used for testing
├── tests/                      # pytest unit + functional tests (42 tests)
├── docs/                       # mkdocs-material documentation source
├── blueprints/                 # Design documents
│   └── hub-design.md           # Original architecture blueprint
├── BACKLOG.md                  # Tracked backlog items with priorities
├── SKILL_CREATE_APP.md         # Skill guide for AI agents creating new apps
├── pyproject.toml              # Hub package definition (hatchling, console scripts)
└── mkdocs.yml                  # Documentation site config
```

**Important runtime directories** (gitignored, created dynamically):
- `apps/` — where installed apps live at runtime (populated by `sqb app add`)
- `sockets/` — fallback Unix socket directory (dev mode)
- `$XDG_DATA_HOME/squareberg/` — sockets, logs, and apps in production

## How the hub works

### Startup

1. Hub loads config from `hub/config.toml`
2. Registry scans `$XDG_DATA_HOME/squareberg/apps/` for directories containing `.squareberg/manifest.toml`
3. For each found app: parse manifest, resolve frontend dist path, assign socket path
4. Hub starts serving on port 9100

### Request routing (priority order)

| Pattern | Handler |
|---------|---------|
| `GET /registry` | List all apps (JSON) |
| `POST /registry/scan` | Re-scan apps directory |
| `GET /registry/{name}` | Single app metadata |
| `GET /registry/{name}/view` | Interactive API explorer (HTML) |
| `GET /registry/{name}/spec` | OpenAPI JSON spec (proxied from app) |
| `POST /registry/{name}/start` | Start app subprocess |
| `POST /registry/{name}/stop` | Stop app subprocess |
| `DELETE /registry/{name}` | Remove app from registry |
| `ANY /apps/{name}/api/{path}` | Reverse proxy to app Unix socket |
| `GET /apps/{name}/{path}` | Serve app's frontend static files |
| `GET /{path}` | Serve hub dashboard (or placeholder) |

### Process model

Each app runs as a **separate uvicorn process** with its own `.venv`. The hub spawns them with `--uds <socket_path>` and manages lifecycle (start, health check, stop, restart). No TCP port allocation needed. The hub reverse-proxies `/apps/{name}/api/*` requests to the app's socket, stripping the prefix.

## How apps are structured

Each app is an **independent repository** with this layout:

```
my-app/
├── .squareberg/
│   └── manifest.toml       # Name, version, backend module, frontend config
├── backend/
│   ├── pyproject.toml       # Python deps (fastapi, uvicorn, app-specific)
│   └── app.py               # FastAPI app with root_path="/apps/{name}"
├── frontend/
│   └── default/             # Preact + daisyUI + Tailwind SPA
│       ├── src/
│       ├── package.json
│       └── dist/            # Built static files (gitignored)
└── data/                    # Per-app SQLite/TinyDB storage (gitignored)
```

### Required contract

Every app backend **must**:
- Set `root_path="/apps/{name}"` on the FastAPI instance
- Expose `GET /api/health` returning `{"status": "ok"}`
- Prefix all routes with `/api/`

### API metadata

Apps should annotate endpoints with `summary`, `description`, `tags`, `response_model`, and `responses` so that both the API explorer and AI agents can introspect the API effectively. See `docs/guide/api-metadata.md` for detailed guidance.

## CLI (`sqb` / `squareberg`)

| Command | Description |
|---------|-------------|
| `sqb start` | Start the hub (foreground) |
| `sqb stop` | Stop the hub |
| `sqb status` | Show hub + app status |
| `sqb app add <source> [--as name]` | Install app from URL or path |
| `sqb app remove <name>` | Uninstall app |
| `sqb app start/stop <name>` | Start/stop a specific app |
| `sqb app logs <name> [-f]` | Tail app logs |
| `sqb app update <name>` | Git pull + rebuild |
| `sqb frontend list <app>` | List bundled frontends |
| `sqb frontend switch <app> <fe>` | Switch active frontend |

The CLI uses `uv` (not pip/venv) for all venv and dependency management.

## Tech stack summary

| Layer | Technology |
|-------|-----------|
| Hub backend | Python, FastAPI, uvicorn, httpx |
| App backends | Python, FastAPI (own venv via uv) |
| IPC | Unix domain sockets |
| Frontends | Preact, Tailwind CSS v4, daisyUI v5, Vite |
| Data storage | SQLite (aiosqlite) or TinyDB per app |
| CLI | Typer + Rich |
| Docs | mkdocs-material |
| Tests | pytest + pytest-asyncio |
| Package manager | uv |

## Key documentation files

| File | Contents |
|------|----------|
| `blueprints/hub-design.md` | Original architecture blueprint (detailed) |
| `docs/guide/writing-apps.md` | Step-by-step guide to creating a new app |
| `docs/guide/api-metadata.md` | How to annotate FastAPI endpoints for the explorer and agents |
| `docs/reference/manifest.md` | Complete manifest.toml schema |
| `docs/reference/hub-api.md` | Hub registry REST API reference |
| `docs/concepts/architecture.md` | Architecture overview with diagrams |
| `SKILL_CREATE_APP.md` | **Interactive skill guide for AI agents creating new apps** |
| `BACKLOG.md` | Tracked development backlog |

## When creating or modifying apps

Refer to `SKILL_CREATE_APP.md` for a structured, interactive workflow that covers API design, implementation, testing, and frontend development. That document is designed to be followed step-by-step with user collaboration at each phase.
