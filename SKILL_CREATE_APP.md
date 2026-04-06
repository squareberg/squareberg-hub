# Skill: Create a Squareberg App

This document guides AI agents through the process of creating a new app for the Squareberg hub. The workflow is **interactive by design** — each phase produces an artifact, pauses for user review, and only proceeds after alignment.

## Prerequisites

Before starting, read these files for context:
- `OVERVIEW.md` — repository structure and how the hub works
- `docs/guide/writing-apps.md` — app structure, manifest, and backend contract
- `docs/guide/api-metadata.md` — how to annotate endpoints for the explorer and agents
- `docs/reference/manifest.md` — complete manifest schema
- `examples/hello/` — reference implementation of the minimal app contract

## Phase 1 — API design

**Goal**: Produce a Markdown document describing the app's backend API.

### Steps

1. **Understand the problem**. Ask the user what the app should do. Clarify the domain, the data it manages, and who/what will interact with it (humans via frontend, other apps, AI agents, all three).

2. **Identify resources and operations**. List the core entities (e.g. "papers", "tasks", "bookmarks") and what operations are needed on each (CRUD, search, import/export, etc.).

3. **Draft endpoints**. For each operation, define:
   - HTTP method and path (under `/api/`)
   - Summary (one line, verb-first)
   - Parameters (query, path, body) with types
   - Response model (fields and types)
   - Error cases (4xx codes and when they occur)

4. **Prioritize into tiers**:
   - **P0 (MVP)**: The minimum set of endpoints needed for the app to be useful. This is what gets implemented first.
   - **P1 (Core)**: Important functionality that rounds out the app but isn't strictly required for a first demo.
   - **P2 (Enhancement)**: Nice-to-have features, advanced queries, bulk operations, etc.

5. **Write the API spec document**. Create `blueprints/{app-name}-api.md` with the full endpoint listing, organized by priority tier. Include example request/response JSON for key endpoints.

6. **Review with user**. Present the document. Expect feedback on scope, naming, missing operations, priority reclassification. Iterate until the user approves the P0 set.

### Output

`blueprints/{app-name}-api.md` — the approved API specification.

---

## Phase 2 — Software architecture

**Goal**: Design the backend's internal structure given the API spec.

### Steps

1. **Identify models**. Map API resources to Python classes / Pydantic models. Define their fields, relationships, and validation rules.

2. **Identify state and storage**. For each model:
   - Does it need persistence? → SQLite table (via `aiosqlite`) or TinyDB collection
   - Is it derived/computed? → No storage, compute on read
   - Does it reference external files? → Store paths, not content

3. **Choose dependencies**. For each non-trivial capability the app needs (PDF parsing, BibTeX import, full-text search, etc.):
   - List 2–3 candidate libraries
   - Note trade-offs (size, maintenance status, Python version support, async compatibility)
   - Recommend one and explain why

4. **Define module structure**. Propose the file layout under `backend/`:
   ```
   backend/
   ├── app.py           # FastAPI app, router mounting
   ├── models.py        # Pydantic models (request/response schemas)
   ├── db.py            # Database setup, connection, migrations
   ├── routes/          # One module per resource (papers.py, tasks.py, etc.)
   └── services/        # Business logic separated from route handlers (if needed)
   ```
   Keep it flat when possible. Don't introduce `routes/` and `services/` unless there are 5+ resources.

5. **Document decisions**. Write `blueprints/{app-name}-architecture.md` with: model definitions, storage choices, dependency selections with rationale, and module layout.

6. **Review with user**. Present the architecture. Expect feedback on dependency choices, storage model, and complexity level. Iterate.

### Output

`blueprints/{app-name}-architecture.md` — the approved architecture document.

---

## Phase 3 — Implementation draft

**Goal**: Implement the P0 endpoints with tests.

### Steps

1. **Scaffold the app directory**:
   ```
   {app-name}/
   ├── .squareberg/manifest.toml
   ├── backend/
   │   ├── pyproject.toml
   │   ├── app.py
   │   ├── models.py
   │   ├── db.py
   │   └── ...
   ├── frontend/default/  (empty for now)
   └── data/
   ```
   Place the app under `examples/{app-name}/` during development so the hub discovers it automatically without needing `sqb app add`.

2. **Implement models** (`models.py`). Define all Pydantic models from the architecture document.

3. **Implement storage** (`db.py`). Set up the database schema or TinyDB collections. Include any seed/migration logic.

4. **Implement P0 routes**. For each endpoint:
   - Follow the API metadata guidelines (`summary`, `description`, `tags`, `response_model`, `responses`, typed parameters with `Query`/`Path`/`Field`)
   - Set `include_in_schema=False` on `/api/health`
   - Keep route handlers thin — delegate to service functions if logic is non-trivial

5. **Write unit tests** for models and service logic:
   - Model validation (valid input, invalid input, edge cases)
   - Database operations (CRUD against a temporary SQLite)
   - Use `tmp_path` fixture for database files

6. **Write functional tests** for the API:
   - Use FastAPI's `TestClient` to test each P0 endpoint
   - Include happy path, validation errors, not-found cases
   - Use synthetic/fixture data (factory functions or JSON fixtures)

7. **Verify the hub contract**:
   - Create a venv: `uv venv examples/{app-name}/.venv`
   - Install deps: `uv pip install -e examples/{app-name}/backend --python examples/{app-name}/.venv/bin/python`
   - Start the hub: `sqb start`
   - Start the app: `sqb app start {app-name}`
   - Verify: `curl http://127.0.0.1:9100/apps/{app-name}/api/health`
   - Check the API explorer: `http://127.0.0.1:9100/registry/{app-name}/view`

8. **Review with user**. Walk through the implementation, test results, and explorer view. Iterate.

### Output

Working P0 backend with passing tests, accessible through the hub.

---

## Phase 4 — Frontend design

**Goal**: Design the app's user interface before writing code.

### Steps

1. **Identify pages/views**. List each screen the user will see. For each:
   - Name and purpose
   - What data it displays (which API endpoints it calls)
   - Key user actions (buttons, forms, navigation)

2. **Define navigation flow**. How does the user move between pages? Draw a simple flow:
   ```
   List view  →  Detail view  →  Edit form
       ↑              ↓
       └── Search ────┘
   ```

3. **Sketch layout** for each page. Describe (don't draw) the layout in structured text:
   ```
   ## Paper List View
   - Top bar: search input (calls GET /api/search?q=...), filter dropdown
   - Main area: table/card grid of papers (title, authors, year, tags)
   - Each item: click to open detail view
   - Floating action button: "Add paper" → import form
   ```

4. **Identify shared components**. What gets reused across pages? (navigation bar, data table, tag input, status badge, etc.)

5. **Write the frontend spec**. Create `blueprints/{app-name}-frontend.md` with pages, flow, layouts, and components.

6. **Review with user**. Expect feedback on page structure, missing views, UX priorities. Iterate.

### Output

`blueprints/{app-name}-frontend.md` — the approved frontend specification.

---

## Phase 5 — Frontend implementation and refinement

**Goal**: Build the frontend and iterate on the full app locally until MVP is reached.

### Steps

1. **Scaffold the frontend** at `frontend/default/`:
   - Vite + Preact + daisyUI + Tailwind v4
   - Configure API proxy in `vite.config.js` for development:
     ```js
     server: { proxy: { '/apps/{app-name}/api': 'http://127.0.0.1:9100' } }
     ```

2. **Implement pages** one at a time, starting with the primary list/dashboard view. Test each page against the running backend.

3. **Development workflow**. Use the following setup for rapid iteration:
   - Terminal 1: `sqb start` (hub on port 9100)
   - Terminal 2: `sqb app start {app-name}` (app backend running)
   - Terminal 3: `cd examples/{app-name}/frontend/default && npm run dev` (Vite dev server with HMR + API proxy)

   The Vite dev server (typically port 5173) serves the frontend with hot reload and proxies API calls to the hub. This gives instant feedback on UI changes without rebuilding.

   > **Note**: The hub does not currently have a built-in dev mode for frontend hot-reloading. The recommended workflow above (Vite dev server proxying to the hub) achieves the same result. A future `sqb dev {app-name}` command could automate this three-terminal setup.

4. **Build and test via hub**. Once a page is working in dev mode, build the frontend and test it served by the hub:
   ```bash
   cd examples/{app-name}/frontend/default && npm run build
   # Refresh http://127.0.0.1:9100/apps/{app-name}/
   ```

5. **Review with user**. Demo the working app in the browser. Expect feedback on layout, UX, missing interactions. Iterate.

### Output

Working MVP with frontend, accessible at `/apps/{app-name}/` through the hub.

---

## Phase 6 — Cleanup and next iteration

**Goal**: Solidify the MVP and plan what comes next.

### Steps

1. **Code review**. Walk through all backend and frontend code:
   - Remove dead code, unused imports, debugging prints
   - Ensure consistent naming and style
   - Verify all P0 endpoints have proper metadata (summary, response_model, etc.)
   - Check test coverage — are there untested error paths?

2. **Update documentation**:
   - Ensure the manifest is accurate
   - Update `blueprints/{app-name}-api.md` if the API changed during implementation
   - Add a brief README.md to the app repo if it will be distributed independently

3. **Re-evaluate the plan**:
   - Review P1 and P2 items from Phase 1. Are they still relevant? Re-prioritize based on what was learned during implementation.
   - Identify any new requirements that emerged.
   - Decide what to tackle next.

4. **Commit and optionally extract**. If the app is ready for independent distribution:
   - Move from `examples/` to its own repository
   - Verify `sqb app add <repo-url>` installs it correctly
   - Verify `sqb app update {app-name}` pulls and rebuilds

5. **Review with user**. Present the cleanup summary and the updated plan for the next iteration.

### Output

Clean, tested, documented MVP. Updated backlog for the next development cycle.

---

## Quick reference

### File locations during development

| What | Where |
|------|-------|
| App source | `examples/{app-name}/` (in-tree, auto-discovered by hub) |
| API spec | `blueprints/{app-name}-api.md` |
| Architecture doc | `blueprints/{app-name}-architecture.md` |
| Frontend spec | `blueprints/{app-name}-frontend.md` |
| App venv | `examples/{app-name}/.venv/` |
| App data | `examples/{app-name}/data/` |
| App logs | `$XDG_DATA_HOME/squareberg/logs/{app-name}.log` |

### Hub contract checklist

- [ ] `.squareberg/manifest.toml` exists and is valid
- [ ] `backend/app.py` exports a `FastAPI` instance
- [ ] `root_path` is set to `/apps/{app-name}`
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] All routes are under `/api/`
- [ ] Endpoints have `summary`, `tags`, and `response_model`
- [ ] `/api/health` has `include_in_schema=False`

### Commands for the development loop

```bash
# One-time setup
uv venv examples/{app-name}/.venv
uv pip install -e examples/{app-name}/backend --python examples/{app-name}/.venv/bin/python

# Start hub + app
sqb start                          # Terminal 1
sqb app start {app-name}           # Terminal 2 (after hub is up)

# Frontend dev (hot reload)
cd examples/{app-name}/frontend/default
npm install && npm run dev         # Terminal 3

# Run tests
.venv/bin/pytest tests/ -v

# Build frontend for hub serving
cd examples/{app-name}/frontend/default && npm run build

# Check the app
curl http://127.0.0.1:9100/apps/{app-name}/api/health
open http://127.0.0.1:9100/registry/{app-name}/view
open http://127.0.0.1:9100/apps/{app-name}/
```
