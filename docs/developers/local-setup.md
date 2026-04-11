# Local Setup

This page covers setting up a local development environment for hacking on the hub itself. If you just want to run Squareberg, see the [Getting Started](../getting-started.md) guide.

## Prerequisites

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.10 | Hub runtime and app backends |
| Node.js | 18 | Building the dashboard SPA |
| `uv` | latest | Python package and venv management |
| Git | any recent | Cloning the repository |

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and Install

```bash
git clone https://github.com/squareberg/squareberg-hub.git
cd squareberg-hub

uv venv --prompt sqb --python 3.12
uv pip install -e ".[dev]"
```

This installs the `sqb` CLI and all development dependencies into the local venv.

```bash
# Option A: activate the venv
source .venv/bin/activate
sqb --help

# Option B: run via uv (no activation needed)
uv run sqb --help
```

## Build the Dashboard

The hub dashboard is a Preact SPA that must be compiled before it can be served:

```bash
./scripts/build-hub.sh
```

The built files land in `hub/dashboard/dist/`. Without them the hub serves a minimal placeholder page, which is fine for backend-only development.

## Run the Tests

```bash
pytest tests/
```

## Serve the Docs Locally

```bash
./scripts/serve-docs.sh
```

Then open `http://127.0.0.1:8000/`.

## Runtime Directories

Squareberg stores runtime data outside the source tree under `$XDG_DATA_HOME/squareberg/` (defaults to `~/.local/share/squareberg/`):

```
~/.local/share/squareberg/
├── apps/       ← installed apps
├── sockets/    ← Unix socket files for running apps
└── logs/       ← per-app log files
```

!!! tip "Next step"
    Continue to the [Hello World walkthrough](hello-world.md) to install and run the bundled example app.
