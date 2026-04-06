# Installation

## Prerequisites

Before installing Squareberg, make sure the following are available on your system:

| Tool | Minimum version | Purpose |
|------|----------------|---------|
| Python | 3.10 | Hub runtime and app backends |
| Node.js | 18 | Building app frontends (build-time only) |
| `uv` | latest | Fast Python package and venv management |
| git | any recent | Cloning app repositories |

To install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

!!! note "Node.js is only needed at build time"
    Node.js is required when building frontend assets (`npm run build`). It is **not** needed at runtime — frontends are served as plain static files by the hub.

## Clone and Install

```bash
git clone https://github.com/jhadida/squareberg
cd squareberg

# Create the virtual environment and install the hub
uv venv
uv pip install -e .
```

This installs the `squareberg` and `sqb` commands into the local venv. Activate it, or prefix commands with `uv run`:

```bash
# Option A: activate
source .venv/bin/activate
sqb --help

# Option B: run via uv (no activation needed)
uv run sqb --help
```

## Verify the Installation

```bash
sqb --help
```

You should see the top-level help listing the available command groups: `start`, `stop`, `status`, `app`, and `frontend`.

## Build the Dashboard

The hub dashboard is a Preact SPA that needs to be compiled before it can be served:

```bash
cd hub/dashboard
npm install
npm run build
cd ../..
```

The built files land in `hub/dashboard/dist/`. If the `dist/` directory is absent, the hub serves a minimal placeholder page instead — this is fine for development but the placeholder has no app controls.

## Optional: Docs Dependencies

To build and serve this documentation locally:

```bash
uv pip install -e ".[docs]"
mkdocs serve
```

Then open `http://127.0.0.1:8000/`.

## What Gets Installed

```
squareberg/
├── .venv/            ← hub virtual environment
├── hub/
│   ├── dashboard/
│   │   └── dist/     ← built dashboard (after npm run build)
│   └── ...
└── examples/         ← in-tree example apps

# Runtime data (created automatically):
# ~/.local/share/squareberg/
#   ├── apps/         ← installed apps
#   ├── sockets/      ← Unix socket files
#   └── logs/         ← per-app log files
```

!!! tip "Next step"
    Continue to the [Hello World walkthrough](hello-world.md) to start the hub and run your first app.
