# CLI Reference

The Squareberg CLI is available as both `sqb` and `squareberg`. Both are identical entry points.

```
sqb [OPTIONS] COMMAND [ARGS]...
```

Commands fall into three groups:

- **Hub lifecycle** — `start`, `stop`, `status`
- **App management** — `app add`, `app remove`, `app list`, `app start`, `app stop`, `app logs`, `app update`
- **Frontend management** — `frontend list`, `frontend switch`

---

## Hub Lifecycle

### `sqb start`

Start the Squareberg hub server in the foreground.

```bash
sqb start
```

The hub reads `hub/config.toml` (falling back to defaults if absent), scans the apps data directory and in-tree `examples/` for apps, mounts static file directories, and begins listening on `127.0.0.1:9100`.

If the hub is already running, the command exits immediately with a notice.

!!! note
    `sqb start` is a foreground process. Use Ctrl-C to stop it, or run it under a service manager — see [Running as a Service](deployment.md).

---

### `sqb stop`

Stop the running hub server.

```bash
sqb stop
```

Locates the hub's uvicorn process using `pgrep` and sends `SIGTERM`. The hub performs a graceful shutdown, stopping all running app subprocesses before exiting.

---

### `sqb status`

Show hub status and a table of registered apps.

```bash
sqb status
```

If the hub is running, app status is fetched live from `GET /registry`. If the hub is stopped, the command scans the filesystem directly (offline mode) and shows `stopped` for all apps.

**Example output:**

```
Hub: running at http://127.0.0.1:9100

  Registered Apps
 ───────────────────────────────────────────────────────────────
  Name    Version  Status   Description
  hello   0.1.0    running  A minimal example app for testing the Squareberg hub
```

---

## App Management

### `sqb app list`

List all installed apps.

```bash
sqb app list
```

Equivalent to `sqb status` but focused on the app table only.

---

### `sqb app add`

Install an app from a GitHub URL or a local path.

```bash
sqb app add <source> [--as NAME]
```

| Argument / Option | Description |
|-------------------|-------------|
| `source` | GitHub URL (`https://github.com/...`) or local directory path |
| `--as NAME` | Install under a custom folder name to avoid name collisions |

**What this command does:**

1. Clones the Git repository (or copies the local directory) into `$XDG_DATA_HOME/squareberg/apps/{name}/`
2. Reads `.squareberg/manifest.toml` to determine the app name
3. Creates a `.venv` in the app directory using `uv venv`
4. Installs Python dependencies: `uv pip install -e backend/`
5. Builds each active frontend: `npm install && npm run build`

**Examples:**

```bash
# Install from a local path
sqb app add examples/hello

# Install from GitHub
sqb app add https://github.com/jhadida/sqb-papers

# Install with a custom name
sqb app add https://github.com/jhadida/sqb-papers --as my-papers
```

!!! warning "Restart required"
    After installing an app, restart the hub for the new app to appear in the registry and dashboard.

---

### `sqb app remove`

Remove an installed app.

```bash
sqb app remove <name>
```

| Argument | Description |
|----------|-------------|
| `name` | Name of the app to remove |

If the hub is running, the app is stopped gracefully before its directory is deleted. The entire app directory is removed from `$XDG_DATA_HOME/squareberg/apps/`, including the venv and data.

**Example:**

```bash
sqb app remove hello
```

---

### `sqb app start`

Start a specific app (hub must be running).

```bash
sqb app start <name>
```

| Argument | Description |
|----------|-------------|
| `name` | Name of the app to start |

Sends `POST /registry/{name}/start` to the hub. The hub spawns the app's uvicorn process and waits for the Unix socket to appear (up to 10 seconds).

**Example:**

```bash
sqb app start hello
```

---

### `sqb app stop`

Stop a specific running app (hub must be running).

```bash
sqb app stop <name>
```

| Argument | Description |
|----------|-------------|
| `name` | Name of the app to stop |

Sends `POST /registry/{name}/stop` to the hub. The hub sends `SIGTERM` to the app process, waits up to 5 seconds, then sends `SIGKILL` if the process has not exited.

**Example:**

```bash
sqb app stop hello
```

---

### `sqb app logs`

Tail an app's log file.

```bash
sqb app logs <name> [-n LINES] [-f]
```

| Argument / Option | Default | Description |
|-------------------|---------|-------------|
| `name` | — | Name of the app |
| `-n`, `--lines` | 50 | Number of lines to show |
| `-f`, `--follow` | false | Follow log output (like `tail -f`) |

Logs are written to `$XDG_DATA_HOME/squareberg/logs/{name}.log` (defaults to `~/.local/share/squareberg/logs/{name}.log`).

**Examples:**

```bash
# Show last 50 lines
sqb app logs hello

# Show last 100 lines and follow
sqb app logs hello -n 100 -f
```

---

### `sqb app update`

Update a git-sourced app (pull latest changes and rebuild).

```bash
sqb app update <name>
```

| Argument | Description |
|----------|-------------|
| `name` | Name of the app to update |

Runs `git pull` in the app's directory, reinstalls Python dependencies, and rebuilds active frontends. The app must have been installed from a Git source (i.e., the app directory must contain a `.git` folder).

**Example:**

```bash
sqb app update hello
```

---

## Frontend Management

### `sqb frontend list`

List bundled frontends for an app and show which are active.

```bash
sqb frontend list <app_name>
```

| Argument | Description |
|----------|-------------|
| `app_name` | Name of the app |

**Example output:**

```
  Frontends for 'hello'
 ───────────────────────────────────────────────
  Name     Display Name  Path              Active
  default  Default       frontend/default  yes
```

---

### `sqb frontend switch`

Activate a different frontend, rebuild it, and update the manifest.

```bash
sqb frontend switch <app_name> <frontend_name>
```

| Argument | Description |
|----------|-------------|
| `app_name` | Name of the app |
| `frontend_name` | Name of the frontend to activate (must exist in the manifest) |

Updates `[frontend] active` in `manifest.toml` to `[frontend_name]`, then runs `npm install && npm run build` in the chosen frontend directory.

**Example:**

```bash
sqb frontend switch hello minimal
```

!!! note
    Restart the hub after switching frontends so the new `dist/` directory is mounted at `/apps/{name}/`.
