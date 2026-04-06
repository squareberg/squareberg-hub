# Frontends

## Frontend Model

Squareberg frontends are **purely client-side single-page applications**. There is no Node server involved at runtime. Vite is used only at build time to compile JSX, resolve imports, and bundle Tailwind CSS — the output is plain static files (HTML, JS, CSS) that the hub serves directly.

This model keeps the hub simple: it only needs to know the path to each app's `dist/` directory. No Node process is kept alive, no server-side rendering occurs.

## Recommended Stack

| Tool | Role |
|------|------|
| [Preact](https://preactjs.com/) | 3KB React-compatible UI framework |
| [Tailwind CSS](https://tailwindcss.com/) | Utility-first CSS framework |
| [daisyUI](https://daisyui.com/) | Component class library on top of Tailwind |
| [Vite](https://vitejs.dev/) | Dev server and production bundler |

This stack produces small bundles and fast builds. Preact's React compatibility means you can use the broader React ecosystem of hooks, libraries, and patterns without the full React runtime size.

## Multiple Frontends Per App

An app can ship more than one frontend under `frontend/`. Each frontend is a separate Vite project with its own `src/`, `package.json`, and `vite.config.js`. Common use cases:

- `default` — the full-featured UI for everyday use
- `minimal` — a stripped-down version for low-power devices or embedding
- `mobile` — an interface optimised for small screens

The `[frontend]` section of the manifest controls which frontends are active:

```toml
[frontend]
active = ["default"]

[frontend.default]
path = "frontend/default"
display_name = "Default"

[frontend.minimal]
path = "frontend/minimal"
display_name = "Minimal"
```

Only frontends listed in `active` are guaranteed to be built and functional with the current backend version. Inactive frontends may exist in the repository but the hub will not serve them.

## How Frontends Are Served

When the hub starts, it scans each registered app's manifest for the first entry in `active`. If that frontend's `dist/` directory exists, the hub mounts it as a static file directory at `/apps/{name}/`:

```
GET /apps/hello/
  → serves {app_dir}/frontend/default/dist/index.html

GET /apps/hello/assets/main.js
  → serves {app_dir}/frontend/default/dist/assets/main.js
```

The mount uses FastAPI's `StaticFiles` with `html=True`, which enables SPA routing (any unmatched path returns `index.html` so the client-side router handles it).

!!! note "Static files are mounted at startup"
    Frontends are mounted when the hub starts. If you build a frontend after the hub is already running, you need to restart the hub for the new files to be served.

## Switching Frontends

To activate a different frontend, use the CLI:

```bash
# See which frontends are available and which is active
sqb frontend list hello

# Switch to the "minimal" frontend
sqb frontend switch hello minimal
```

`sqb frontend switch` updates the `active` list in the manifest and runs `npm install && npm run build` in the new frontend's directory. After the switch, restart the hub so the new `dist/` path is mounted.

## Apps Without Frontends

An app is not required to ship a frontend. An app with no active frontend is still fully usable:

- Its API is accessible via `/apps/{name}/api/*`
- Its OpenAPI spec is available at `/registry/{name}/spec`
- FastAPI's built-in Swagger UI and ReDoc are reachable at the app's own socket (useful during development)

The hub dashboard shows all registered apps regardless of whether they have a frontend.

## Frontend Development Workflow

During development, you can run Vite's dev server alongside the hub. Because all API calls go through the hub, configure Vite to proxy API requests:

```javascript
// vite.config.js
import { defineConfig } from 'vite'
import preact from '@preact/preset-vite'

export default defineConfig({
  plugins: [preact()],
  server: {
    proxy: {
      '/apps/hello/api': 'http://127.0.0.1:9100',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

Run `npm run dev` in the frontend directory while `sqb start` is running in another terminal. The Vite dev server handles hot module replacement; the hub handles the actual API calls.
