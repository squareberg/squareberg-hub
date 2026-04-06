import { useState } from "preact/hooks";

const STATUS_BADGE = {
  running: "badge-success",
  stopped: "badge-ghost",
  error: "badge-error",
};

export function AppCard({ app, onRefresh }) {
  const [busy, setBusy] = useState(false);
  const isRunning = app.status === "running";

  async function toggle() {
    setBusy(true);
    try {
      const action = isRunning ? "stop" : "start";
      await fetch(`/registry/${app.name}/${action}`, { method: "POST" });
      await onRefresh();
    } catch (err) {
      console.error("Action failed:", err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div class="card bg-base-100 shadow-md">
      <div class="card-body">
        <div class="flex items-center justify-between">
          <h2 class="card-title text-lg">{app.display_name}</h2>
          <span class={`badge ${STATUS_BADGE[app.status] || "badge-ghost"}`}>
            {app.status}
          </span>
        </div>

        <p class="text-sm opacity-70">{app.description}</p>

        <div class="text-xs opacity-50 mt-1">v{app.version}</div>

        <div class="card-actions justify-end mt-4">
          <a
            class="btn btn-sm btn-outline"
            href={`/apps/${app.name}/`}
            target="_blank"
            rel="noopener"
          >
            Open
          </a>
          <a
            class="btn btn-sm btn-outline"
            href={`/registry/${app.name}/view`}
            target="_blank"
            rel="noopener"
          >
            API
          </a>
          <button
            class={`btn btn-sm ${isRunning ? "btn-error" : "btn-success"}`}
            onClick={toggle}
            disabled={busy}
          >
            {busy ? (
              <span class="loading loading-spinner loading-xs" />
            ) : isRunning ? (
              "Stop"
            ) : (
              "Start"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
