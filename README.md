# Squareberg

A local application hub that aggregates personal productivity tools behind a unified API gateway. Each app is a standalone FastAPI backend with its own virtual environment, communicating over Unix domain sockets. Frontends are fully decoupled client-side SPAs.

## Features

- **Unified dashboard** — grid launcher showing all apps, status, and links
- **Decoupled frontends** — each app ships one or more Preact + daisyUI SPAs; no Node runtime at runtime
- **Per-app isolation** — separate process, venv, and SQLite database per app
- **OpenAPI introspection** — live spec exposure for human browsing and agentic discovery
- **`sqb` CLI** — install, start, stop, update apps; switch frontends
- **macOS + Linux** — Unix sockets, `uv`, `npm`; no Docker, no external database server

## Requirements

- Python ≥ 3.10
- Node.js ≥ 18
- [`uv`](https://docs.astral.sh/uv/)
- Git

## Quick start

```bash
git clone https://github.com/jhadida/squareberg
cd squareberg
uv venv && uv pip install -e .

# Build the dashboard
cd hub/dashboard && npm install && npm run build && cd ../..

# Start the hub (port 9100)
sqb start
```

Open `http://127.0.0.1:9100` in your browser.

Install the hello-world example app to verify the pipeline:

```bash
sqb app add examples/hello
sqb app start hello
# → http://127.0.0.1:9100/apps/hello/
```

## CLI

```
sqb start / stop / status
sqb app add <url-or-path> [--as <name>]
sqb app remove / start / stop / logs / update <name>
sqb frontend list / switch <app> <frontend>
```

## Documentation

Full docs at [jhadida.github.io/squareberg](https://jhadida.github.io/squareberg) — or build locally:

```bash
uv pip install -e ".[docs]"
mkdocs serve
```

## Project layout

```
squareberg/
├── hub/            # hub backend (FastAPI, proxy, registry, process manager)
│   └── dashboard/  # hub dashboard SPA (Preact + daisyUI + Tailwind)
├── examples/
│   └── hello/      # minimal example app
├── docs/           # mkdocs-material documentation source
└── tests/          # pytest unit and functional tests
```

## License

MIT
