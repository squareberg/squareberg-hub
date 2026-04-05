# manifest.toml Reference

Every Squareberg app declares itself via `.squareberg/manifest.toml`. This file is required — without it the hub will not discover or register the app.

## `[app]` Section

General metadata about the app.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | — | Short, unique identifier. Used as the URL prefix (`/apps/{name}/`), directory name in `apps/`, and socket filename. Must be lowercase, with hyphens allowed. |
| `display_name` | string | no | value of `name` | Human-readable name shown in the dashboard. |
| `description` | string | no | `""` | One-line description shown in the dashboard. |
| `version` | string | no | `"0.0.0"` | Semantic version string. Shown in `sqb status` output. |

## `[backend]` Section

How the hub launches the app's FastAPI backend.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `module` | string | no | `"app:app"` | The uvicorn module target, in `module:attribute` format. Resolved relative to `backend/`. |

The hub spawns the backend as:

```
<app>/.venv/bin/python -m uvicorn <module> --uds <socket_path> --app-dir <app>/backend/
```

## `[frontend]` Section

Controls which frontends are active and served by the hub.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `active` | list of strings | no | `[]` | Names of frontends that are built and served. The hub mounts the first entry's `dist/` at `/apps/{name}/`. |

## `[frontend.<name>]` Subsections

One subsection per named frontend. The `<name>` must appear in the `active` list to be served.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `path` | string | no | `"frontend/<name>"` | Path to the frontend directory relative to the app root. |
| `display_name` | string | no | value of `<name>` | Human-readable name shown in `sqb frontend list` output. |

## Complete Example

```toml
[app]
name = "papers"
display_name = "Papers"
description = "Research paper and document library"
version = "0.2.1"

[backend]
module = "app:app"

[frontend]
active = ["default"]

[frontend.default]
path = "frontend/default"
display_name = "Default"

[frontend.minimal]
path = "frontend/minimal"
display_name = "Minimal"
```

In this example, `default` is the active frontend and `minimal` is bundled but inactive. Switching to `minimal` via `sqb frontend switch papers minimal` would update the `active` list and rebuild.

## Notes

!!! tip "Name uniqueness"
    App names must be unique across all installed apps and in-tree examples. If two manifests declare the same `name`, the second one encountered during the registry scan is skipped with a warning.

!!! warning "URL safety"
    The `name` field is used directly in URL paths. Stick to lowercase letters, digits, and hyphens. Avoid spaces, underscores, or special characters.
