# Getting Started

## Prerequisites

Squareberg requires only two things:

| Tool | Minimum version | Notes |
|------|----------------|-------|
| Python | 3.10 | 3.12 recommended |
| `uv` | latest | Python package manager |

Install `uv` if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Node.js is **not** required — the dashboard is bundled as pre-built static files.

## Install

```bash
uv tool install squareberg-hub
```

This installs the `sqb` command globally. Verify:

```bash
sqb --help
```

## Start the Hub

```bash
sqb start
```

The hub starts at `http://127.0.0.1:9100`. Open it in your browser to see the dashboard.

!!! note "Foreground process"
    `sqb start` runs in the foreground. See [Running as a Service](guide/deployment.md) for background operation and auto-start on login.

## Install Your First App

Apps are independent repositories installed with:

```bash
sqb app add <git-url-or-local-path>
sqb app start <name>
```

The hub then proxies the app's API at `/apps/<name>/api/` and serves its frontend at `/apps/<name>/`.

!!! tip "Building your own app"
    See [Writing Apps](guide/writing-apps.md) for a step-by-step guide to creating a Squareberg app.

## Update

```bash
uv tool upgrade squareberg-hub
```
