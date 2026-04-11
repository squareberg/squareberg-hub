# Squareberg

Squareberg is a **local application hub** that aggregates personal productivity tools behind a unified API gateway. Each app is a standalone FastAPI backend running in its own virtual environment, communicating with the hub over Unix domain sockets. Frontends are decoupled from backends: every app ships its own client-side SPA, while the hub provides a dashboard launcher and a generic OpenAPI introspection layer.

Apps are developed and distributed as independent repositories. Installed apps live under `$XDG_DATA_HOME/squareberg/apps/` (defaults to `~/.local/share/squareberg/apps/`), keeping runtime data out of the source tree.

## Key Features

- **Unified dashboard** — a single launcher UI showing all installed apps, their status, and quick links to each app's UI and API docs
- **Decoupled frontends** — each app ships its own client-side SPA; the hub serves it as static files with no Node runtime required at runtime
- **Per-app process isolation** — every app runs as a separate subprocess with its own Python virtual environment, so a crash or dependency conflict in one app cannot affect others
- **Per-app venv** — dependencies are installed into `<app>/.venv` using `uv`, keeping the hub environment minimal
- **OpenAPI introspection** — each app's OpenAPI spec is fetched live and exposed through the hub, enabling both a human-readable API browser and programmatic discovery by AI agents
- **`sqb` CLI** — a single command-line tool (also available as `squareberg`) covering hub lifecycle, app management, and frontend switching
- **macOS and Linux** — targets macOS as the primary platform with Linux support planned; Windows is out of scope
- **No Docker required** — Unix sockets, `uv`, and `npm` are all that's needed; no container runtime, no external database server

## Quick Start

```bash
# Install
uv tool install squareberg-hub

# Start the hub
sqb start
```

Open `http://127.0.0.1:9100` in your browser.

## Next Steps

- [Getting Started](getting-started.md) — install and run the hub
- [Architecture overview](concepts/architecture.md) — how the hub, apps, and frontends fit together
- [Writing Apps](guide/writing-apps.md) — create your own Squareberg app
