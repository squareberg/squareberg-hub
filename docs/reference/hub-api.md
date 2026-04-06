# Hub API

The hub exposes a small REST API under `/registry` for discovering apps, checking their status, fetching OpenAPI specs, and controlling app lifecycle. All endpoints return JSON.

The hub runs on `http://127.0.0.1:9100` by default.

---

## `GET /registry`

List all registered apps with their current status.

### Request

No parameters.

### Response

HTTP 200 — array of app objects.

```json
[
  {
    "name": "hello",
    "display_name": "Hello World",
    "description": "A minimal example app for testing the Squareberg hub",
    "version": "0.1.0",
    "status": "running",
    "socket_path": "/home/user/.local/share/squareberg/sockets/hello.sock",
    "frontend_dist_path": "/home/user/.local/share/squareberg/apps/hello/frontend/default/dist",
    "manifest_path": "/home/user/.local/share/squareberg/apps/hello/.squareberg/manifest.toml",
    "backend_module": "app:app"
  }
]
```

### Status Values

| Value | Meaning |
|-------|---------|
| `stopped` | App process is not running |
| `running` | App process is live and its socket file exists |
| `error` | App process exited unexpectedly or timed out during startup |

---

## `GET /registry/{name}`

Get metadata and current status for a single app.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | App name as declared in `manifest.toml` |

### Response

HTTP 200 — single app object (same schema as the items in `GET /registry`).

```json
{
  "name": "hello",
  "display_name": "Hello World",
  "description": "A minimal example app for testing the Squareberg hub",
  "version": "0.1.0",
  "status": "running",
  "socket_path": "/home/user/.local/share/squareberg/sockets/hello.sock",
  "frontend_dist_path": "/home/user/.local/share/squareberg/apps/hello/frontend/default/dist",
  "manifest_path": "/home/user/.local/share/squareberg/apps/hello/.squareberg/manifest.toml",
  "backend_module": "app:app"
}
```

### Error Codes

| Code | Condition |
|------|-----------|
| 404 | No app with the given name is registered |

---

## `GET /registry/{name}/spec`

Fetch the app's live OpenAPI JSON spec by proxying `GET /openapi.json` to its Unix socket.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | App name |

### Response

HTTP 200 — the app's OpenAPI spec as returned by FastAPI. The structure conforms to the OpenAPI 3.x specification.

```json
{
  "openapi": "3.1.0",
  "info": {
    "title": "Hello World",
    "version": "0.1.0"
  },
  "paths": {
    "/api/health": {
      "get": {
        "summary": "Health",
        "operationId": "health_api_health_get",
        "responses": {
          "200": {
            "description": "Successful Response"
          }
        }
      }
    }
  }
}
```

### Error Codes

| Code | Condition |
|------|-----------|
| 404 | App not found |
| 503 | App is not running; start it first |
| 502 | Failed to reach the app's socket (proxy error) |

---

## `POST /registry/{name}/start`

Start an app.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | App name |

### Request Body

None.

### Response

HTTP 200 — confirmation object.

```json
{
  "status": "ok",
  "app": "hello",
  "message": "App 'hello' started."
}
```

The hub spawns the uvicorn process and waits up to 10 seconds for the Unix socket file to appear. If the process exits immediately or the socket does not appear in time, a 500 error is returned and the app is marked as `error`.

### Error Codes

| Code | Condition |
|------|-----------|
| 404 | App not found |
| 500 | App process failed to start; check app logs |

---

## `POST /registry/{name}/stop`

Stop a running app.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | App name |

### Request Body

None.

### Response

HTTP 200 — confirmation object.

```json
{
  "status": "ok",
  "app": "hello",
  "message": "App 'hello' stopped."
}
```

The hub sends `SIGTERM` to the app process and waits up to 5 seconds for a graceful exit. If the process does not exit in time, `SIGKILL` is sent. The socket file is removed and the app status is set to `stopped`.

Calling stop on an app that is already stopped is a no-op and returns HTTP 200.

### Error Codes

| Code | Condition |
|------|-----------|
| 404 | App not found |
| 500 | Unexpected error during shutdown |
