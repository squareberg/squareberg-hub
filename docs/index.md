# Squareberg

Squareberg is a **local application hub** that aggregates personal productivity tools behind a unified API gateway. Each app is a standalone FastAPI backend running in its own virtual environment, communicating with the hub over Unix domain sockets. Frontends are decoupled from backends: every app ships its own client-side SPA, while the hub provides a dashboard launcher and a generic OpenAPI introspection layer.

Apps are developed and distributed as independent repositories. The hub's `apps/` directory is a runtime-only location where apps are installed via the `sqb` CLI.

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
# 1. Install the hub
git clone https://github.com/jhadida/squareberg
cd squareberg
uv venv && uv pip install -e .

# 2. Build the dashboard
cd hub/dashboard && npm install && npm run build && cd ../..

# 3. Start the hub
sqb start

# 4. In a second terminal, install and start the hello-world app
sqb app add examples/hello
sqb app start hello

# 5. Open the app in your browser
open http://127.0.0.1:9100/apps/hello/
```

!!! tip "Dashboard"
    The hub dashboard at `http://127.0.0.1:9100/` shows all registered apps with start/stop controls and links to their UIs and API specs.

## Next Steps

- [Installation](getting-started/installation.md) — detailed prerequisites and setup
- [Hello World walkthrough](getting-started/hello-world.md) — step-by-step first run
- [Architecture overview](concepts/architecture.md) — how the hub, apps, and frontends fit together
- [Writing Apps](guide/writing-apps.md) — create your own Squareberg app
