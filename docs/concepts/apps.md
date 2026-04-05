# Apps

## What Is a Squareberg App?

A Squareberg app is an **independent repository** containing:

- A **FastAPI backend** that runs as a subprocess managed by the hub
- One or more **frontend SPAs** built with Vite (optional but recommended)
- A **manifest file** (`.squareberg/manifest.toml`) that declares the app's metadata and entry points

Apps are self-contained units. They do not import from each other, and they manage their own data storage. The hub provides process management, reverse proxying, and static file serving — nothing more.

## Repository Layout

```
my-app/
├── .squareberg/
│   └── manifest.toml        # app metadata, backend entry, frontend registry
├── backend/
│   ├── pyproject.toml        # Python dependencies
│   ├── app.py                # FastAPI entry point
│   ├── models.py             # (optional) data models
│   ├── db.py                 # (optional) database helpers
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

The `data/` directory is where the app stores its database files and other runtime artifacts. It should be gitignored.

## Manifest Schema

The manifest file lives at `.squareberg/manifest.toml` and is the single source of truth for how the hub discovers and manages the app.

```toml
[app]
name = "hello"
display_name = "Hello World"
description = "A minimal example app for testing the Squareberg hub"
version = "0.1.0"

[backend]
module = "app:app"

[frontend]
active = ["default"]

[frontend.default]
path = "frontend/default"
display_name = "Default"
```

See [manifest.toml reference](../reference/manifest.md) for the full field listing.

## FastAPI Entry Point Contract

Every app must expose a FastAPI application object that satisfies two requirements:

**1. Set `root_path` to match the hub mount point.**

The hub proxies all requests to `/apps/{name}/api/*`. The app must tell FastAPI about this prefix so that OpenAPI spec URLs, redirect responses, and documentation links are generated correctly:

```python
# backend/app.py
from fastapi import FastAPI

app = FastAPI(
    title="Hello World",
    version="0.1.0",
    root_path="/apps/hello",   # must match hub mount point
)
```

**2. Expose `GET /api/health`.**

The hub uses this endpoint to verify that an app process has started successfully and to perform ongoing health checks:

```python
@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

The health endpoint must return HTTP 200. Any non-200 response (or a connection error) causes the hub to mark the app as unhealthy.

A minimal but complete backend:

```python
from fastapi import FastAPI

app = FastAPI(
    title="Hello World",
    version="0.1.0",
    root_path="/apps/hello",
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/greet")
async def greet(name: str = "world"):
    return {"message": f"Hello, {name}!"}
```

## Data Storage

### SQLite (default)

The recommended storage for most apps. Each app maintains its own SQLite database in its `data/` directory.

```python
# backend/db.py
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "app.db"

async def get_connection():
    return await aiosqlite.connect(DB_PATH)
```

Benefits: zero configuration, per-app isolation, simple backups (copy the file), async support via `aiosqlite`.

### TinyDB (document-style)

For apps that need a flexible, schema-free data model:

```python
from tinydb import TinyDB, Query
from pathlib import Path

db = TinyDB(Path(__file__).parent.parent / "data" / "store.json")

# Insert
db.insert({"url": "https://example.com", "tags": ["productivity"]})

# Query
Item = Query()
results = db.search(Item.tags.any(["productivity"]))
```

TinyDB is well-suited for small datasets (bookmarks, settings, metadata). If an app needs complex queries or high write throughput, prefer SQLite.

## Inter-App Communication

Apps must not import from each other's code. If one app needs data from another, it makes an HTTP request through the hub:

```python
import httpx

async def fetch_paper_metadata(paper_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"http://127.0.0.1:9100/apps/papers/api/papers/{paper_id}"
        )
        resp.raise_for_status()
        return resp.json()
```

This pattern ensures that any app can be stopped, replaced, or moved independently without breaking imports in other apps.

!!! warning "Hub must be running"
    Inter-app calls go through the hub. If the hub is not running, these calls will fail. Design your apps to handle the case where a dependency app is unavailable.
