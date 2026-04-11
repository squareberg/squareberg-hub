# Squareberg

A local application hub that aggregates personal productivity tools behind a unified API gateway. Each app is a standalone FastAPI backend with its own virtual environment, communicating over Unix domain sockets. Frontends are fully decoupled client-side SPAs.

## Features

- **Unified dashboard** — grid launcher showing all apps, status, and links
- **Decoupled frontends** — each app ships one or more Preact + daisyUI SPAs; no Node runtime at runtime
- **Per-app isolation** — separate process, venv, and SQLite database per app
- **OpenAPI introspection** — live spec exposure for human browsing and agentic discovery
- **`sqb` CLI** — install, start, stop, update apps; switch frontends
- **macOS + Linux** — Unix sockets, `uv`; no Docker, no external database server

<p align="center"><img src="logo-square.png" width="75%"></p>

## Requirements

- Python ≥ 3.10
- [`uv`](https://docs.astral.sh/uv/)

## Quick Start

```bash
uv tool install squareberg-hub
sqb start
```

Open `http://127.0.0.1:9100` in your browser.

## CLI

```
sqb start / stop / status
sqb app add <url-or-path> [--as <name>]
sqb app remove / start / stop / logs / update <name>
sqb frontend list / switch <app> <frontend>
```

## Documentation

Full docs at [squareberg.github.io/squareberg-hub](https://squareberg.github.io/squareberg-hub), including a guide for writing your own apps.

For local development and contributing, see the [Developers](https://squareberg.github.io/squareberg-hub/developers/local-setup/) section of the docs.

## License

MIT
