# Writing Apps

This guide walks through creating a new Squareberg app from scratch, from directory structure through to installing it into the hub.

## 1. Create the Directory Structure

```bash
mkdir -p my-app/.squareberg
mkdir -p my-app/backend
mkdir -p my-app/frontend/default/src
mkdir -p my-app/data
```

Your working tree should look like:

```
my-app/
├── .squareberg/
├── backend/
├── frontend/
│   └── default/
│       └── src/
└── data/
```

## 2. Write the Manifest

Create `.squareberg/manifest.toml`:

```toml
[app]
name = "my-app"
display_name = "My App"
description = "What this app does"
version = "0.1.0"

[backend]
module = "app:app"

[frontend]
active = ["default"]

[frontend.default]
path = "frontend/default"
display_name = "Default"
```

The `name` field must be a short, lowercase, hyphen-separated identifier. It is used as the URL prefix (`/apps/my-app/`) and the directory name under `apps/`.

## 3. Write the Backend

### `backend/pyproject.toml`

```toml
[project]
name = "my-app-backend"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "aiosqlite>=0.21",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["."]
```

### `backend/app.py`

Every Squareberg backend must:

1. Set `root_path` to `/apps/{name}` so FastAPI generates correct spec URLs
2. Expose `GET /api/health` returning `{"status": "ok"}`

```python
from fastapi import FastAPI

app = FastAPI(
    title="My App",
    version="0.1.0",
    root_path="/apps/my-app",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/hello")
async def hello(name: str = "world"):
    return {"message": f"Hello, {name}!"}
```

All application routes should live under `/api/` to keep them separate from the frontend path namespace.

## 4. Set Up the Frontend

### Install Vite with Preact

```bash
cd my-app/frontend/default
npm create vite@latest . -- --template preact
npm install
npm install -D tailwindcss daisyui @tailwindcss/vite
```

### `frontend/default/vite.config.js`

```javascript
import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    preact(),
    tailwindcss(),
  ],
  // Proxy API calls to the hub during development
  server: {
    proxy: {
      '/apps/my-app/api': 'http://127.0.0.1:9100',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

### `frontend/default/src/main.jsx`

A minimal entry point:

```jsx
import { render } from 'preact'
import { useState } from 'preact/hooks'

function App() {
  const [message, setMessage] = useState('')

  async function greet() {
    const resp = await fetch('/apps/my-app/api/hello?name=Squareberg')
    const data = await resp.json()
    setMessage(data.message)
  }

  return (
    <div class="min-h-screen bg-base-200 flex items-center justify-center">
      <div class="card bg-base-100 shadow-xl p-8">
        <h1 class="text-2xl font-bold mb-4">My App</h1>
        <button class="btn btn-primary" onClick={greet}>Say hello</button>
        {message && <p class="mt-4">{message}</p>}
      </div>
    </div>
  )
}

render(<App />, document.getElementById('app'))
```

### Configure Tailwind

Create `frontend/default/src/index.css`:

```css
@import "tailwindcss";
@plugin "daisyui";
```

Import it in your entry HTML or `main.jsx`.

## 5. Test Locally

Before installing into the hub, verify the backend works standalone:

```bash
# Create a venv and install deps
cd my-app
uv venv
uv pip install -e backend/

# Run the backend directly
.venv/bin/uvicorn app:app --app-dir backend/ --port 8001 --reload
```

Open `http://127.0.0.1:8001/api/health` — you should see `{"status": "ok"}`.

For the frontend:

```bash
cd frontend/default
npm run dev
```

Open the Vite dev server URL (typically `http://127.0.0.1:5173/`). API calls proxy to the hub on port 9100 (make sure `sqb start` is running if you test API calls).

## 6. Install into the Hub

```bash
# From the squareberg project root
sqb app add /path/to/my-app
```

This copies the app into `apps/my-app/`, creates a fresh venv, installs backend deps, and builds the frontend.

Then restart the hub and start the app:

```bash
# Restart the hub so it picks up the new app
sqb stop
sqb start &

# In another terminal
sqb app start my-app
```

Navigate to `http://127.0.0.1:9100/apps/my-app/` to see your app.

!!! tip "During development"
    While iterating, you can skip `sqb app add` and just point the hub at your local directory. Since the registry scans `examples/` automatically, placing your app under `examples/my-app/` lets you test without copying.
