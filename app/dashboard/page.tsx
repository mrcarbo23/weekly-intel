"use client";
import { useState, useEffect } from "react";

interface Source {
  id: number;
  name: string;
  source_type: string;
  url: string;
  active: boolean;
  last_fetched_at: string | null;
}

export default function Dashboard() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [newSource, setNewSource] = useState({ name: "", source_type: "substack", url: "" });

  useEffect(() => {
    fetchSources();
  }, []);

  const fetchSources = async () => {
    const res = await fetch("/api/sources");
    if (res.ok) setSources(await res.json());
  };

  const addSource = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch("/api/sources", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(newSource),
    });
    if (res.ok) {
      setNewSource({ name: "", source_type: "substack", url: "" });
      fetchSources();
    }
  };

  const runPipeline = async (step: "ingest" | "process" | "digest") => {
    setLoading(true);
    setStatus(`Running ${step}...`);
    try {
      const res = await fetch(`/api/${step}`, { method: "POST" });
      const data = await res.json();
      setStatus(`✅ ${step} complete: ${JSON.stringify(data)}`);
    } catch (e) {
      setStatus(`❌ Error: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-8">📬 Weekly Intel Dashboard</h1>

      {/* Pipeline Controls */}
      <section className="bg-white rounded-xl border shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Pipeline Controls</h2>
        <div className="flex gap-3 flex-wrap">
          <button
            onClick={() => runPipeline("ingest")}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            1. Ingest Sources
          </button>
          <button
            onClick={() => runPipeline("process")}
            disabled={loading}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            2. Process with AI
          </button>
          <button
            onClick={() => runPipeline("digest")}
            disabled={loading}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            3. Generate Digest
          </button>
        </div>
        {status && (
          <p className="mt-4 text-sm text-gray-700 bg-gray-50 p-3 rounded">{status}</p>
        )}
      </section>

      {/* Sources */}
      <section className="bg-white rounded-xl border shadow-sm p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Sources ({sources.length})</h2>

        {sources.length === 0 ? (
          <p className="text-gray-500 text-sm">No sources configured yet.</p>
        ) : (
          <div className="space-y-2">
            {sources.map((s) => (
              <div key={s.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2 py-1 rounded uppercase">
                  {s.source_type}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm">{s.name}</p>
                  <p className="text-xs text-gray-500 truncate">{s.url}</p>
                </div>
                <span className={`text-xs ${s.active ? "text-green-600" : "text-gray-400"}`}>
                  {s.active ? "Active" : "Inactive"}
                </span>
                {s.last_fetched_at && (
                  <span className="text-xs text-gray-400">
                    Last: {new Date(s.last_fetched_at).toLocaleDateString()}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Add source form */}
        <form onSubmit={addSource} className="mt-4 flex gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Source name"
            value={newSource.name}
            onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
            className="border rounded px-3 py-2 text-sm flex-1 min-w-32"
            required
          />
          <select
            value={newSource.source_type}
            onChange={(e) => setNewSource({ ...newSource, source_type: e.target.value })}
            className="border rounded px-3 py-2 text-sm"
          >
            <option value="substack">Substack</option>
            <option value="gmail">Gmail</option>
            <option value="youtube">YouTube</option>
          </select>
          <input
            type="url"
            placeholder="URL"
            value={newSource.url}
            onChange={(e) => setNewSource({ ...newSource, url: e.target.value })}
            className="border rounded px-3 py-2 text-sm flex-1 min-w-48"
          />
          <button
            type="submit"
            className="bg-gray-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-900"
          >
            Add Source
          </button>
        </form>
      </section>
    </div>
  );
}
