import { useState, useEffect, useCallback } from "preact/hooks";
import { AppCard } from "./components/AppCard";

export function App() {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchApps = useCallback(async () => {
    try {
      const res = await fetch("/registry");
      if (res.ok) {
        setApps(await res.json());
      }
    } catch (err) {
      console.error("Failed to fetch apps:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchApps();
    const interval = setInterval(fetchApps, 5000);
    return () => clearInterval(interval);
  }, [fetchApps]);

  return (
    <div class="min-h-screen bg-base-200">
      <div class="navbar bg-base-100 shadow-sm">
        <div class="navbar-start">
          <span class="text-xl font-bold px-4">Squareberg</span>
        </div>
        <div class="navbar-center">
          <span class="text-sm opacity-60">Local Application Hub</span>
        </div>
        <div class="navbar-end" />
      </div>

      <main class="container mx-auto p-6">
        {loading ? (
          <div class="flex justify-center py-20">
            <span class="loading loading-spinner loading-lg" />
          </div>
        ) : apps.length === 0 ? (
          <div class="text-center py-20 opacity-60">
            No applications registered.
          </div>
        ) : (
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {apps.map((app) => (
              <AppCard key={app.name} app={app} onRefresh={fetchApps} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
