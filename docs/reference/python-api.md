# Python API

Auto-generated reference for the public Python modules in the `hub` package.

!!! note "When to use this"
    This reference is useful if you are extending the hub itself, writing tests, or scripting against the hub's internals. For most app development, the [CLI](../guide/cli.md) and [Hub API](hub-api.md) are sufficient.

---

## hub.config

Configuration loading and directory resolution. The `HubConfig` dataclass holds all runtime settings; helper functions resolve the paths used by the hub at startup.

::: hub.config
    options:
      members:
        - HubConfig
        - load_config
        - get_socket_dir
        - get_log_dir
        - get_apps_dir

---

## hub.registry

App discovery and runtime status tracking. The `Registry` class scans the filesystem for manifests and maintains an in-memory map of app names to `AppInfo` objects.

::: hub.registry
    options:
      members:
        - AppInfo
        - Registry

---

## hub.manager

Process lifecycle management. `ProcessManager` spawns uvicorn subprocesses for apps, waits for their sockets to appear, and handles graceful shutdown.

::: hub.manager
    options:
      members:
        - ProcessManager
