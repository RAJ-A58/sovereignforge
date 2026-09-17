"use client";

import { useState, useEffect } from "react";

interface KBStats {
  total_chunks: number;
  sources: Record<string, number>;
  ready: boolean;
}

export default function KnowledgeBasePanel() {
  const [stats, setStats] = useState<KBStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const fetchStats = async () => {
    try {
      const r = await fetch("http://localhost:8000/api/kb/stats");
      if (r.ok) setStats(await r.json());
    } catch {
      // backend may not be running yet
    }
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFileIngest = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const r = await fetch("http://localhost:8000/api/kb/ingest-file?doc_type=document", {
        method: "POST",
        body: formData,
      });
      const data = await r.json();
      if (data.success) {
        setMessage(`✅ Ingested ${data.chunks_added} chunks from "${file.name}"`);
        fetchStats();
      } else {
        setMessage(`❌ ${data.error}`);
      }
    } catch (err) {
      setMessage(`❌ ${err instanceof Error ? err.message : "Upload failed"}`);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleClear = async () => {
    if (!confirm("Clear all knowledge base documents?")) return;
    try {
      await fetch("http://localhost:8000/api/kb/clear", { method: "DELETE" });
      setMessage("🗑 Knowledge base cleared.");
      fetchStats();
    } catch {
      setMessage("❌ Failed to clear KB");
    }
  };

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
      {/* Header — always visible */}
      <button
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800 transition"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2">
          <span className="text-blue-400 text-sm">📚</span>
          <span className="text-sm font-semibold text-gray-200">Knowledge Base</span>
          {stats && (
            <span
              className={`ml-1 text-xs px-2 py-0.5 rounded-full border ${
                stats.ready
                  ? "text-green-400 bg-green-400/10 border-green-400/20"
                  : "text-gray-500 bg-gray-800 border-gray-700"
              }`}
            >
              {stats.ready ? `${stats.total_chunks} chunks` : "Empty"}
            </span>
          )}
        </div>
        <span className="text-gray-600 text-xs">{expanded ? "▲" : "▼"}</span>
      </button>

      {/* Expandable body */}
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-800">
          {/* Sources list */}
          {stats && Object.keys(stats.sources).length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-500 mb-1 font-semibold uppercase tracking-wide">
                Ingested Sources
              </p>
              <div className="space-y-1">
                {Object.entries(stats.sources).map(([src, count]) => (
                  <div
                    key={src}
                    className="flex items-center justify-between text-xs bg-gray-800 rounded px-2 py-1"
                  >
                    <span className="text-gray-300 truncate max-w-[160px]" title={src}>
                      📄 {src}
                    </span>
                    <span className="text-gray-500 ml-2 shrink-0">{count} chunks</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload button */}
          <div>
            <label className="block">
              <span className="text-xs text-gray-500 mb-1 block">Add Document to KB</span>
              <div className="flex items-center gap-2">
                <label
                  className={`cursor-pointer px-3 py-1.5 text-xs rounded-lg border transition ${
                    uploading
                      ? "bg-gray-800 border-gray-700 text-gray-500 cursor-not-allowed"
                      : "bg-blue-600/20 border-blue-600/40 text-blue-400 hover:bg-blue-600/30"
                  }`}
                >
                  {uploading ? "Ingesting..." : "📎 Ingest File"}
                  <input
                    type="file"
                    className="hidden"
                    onChange={handleFileIngest}
                    disabled={uploading}
                    accept=".txt,.pdf,.docx,.md"
                  />
                </label>
                {stats && stats.total_chunks > 0 && (
                  <button
                    onClick={handleClear}
                    className="px-3 py-1.5 text-xs rounded-lg border border-red-400/30 text-red-400 hover:bg-red-400/10 transition"
                  >
                    🗑 Clear KB
                  </button>
                )}
              </div>
            </label>
          </div>

          {/* Status message */}
          {message && (
            <p className="text-xs text-gray-400 bg-gray-800 px-2 py-1.5 rounded">{message}</p>
          )}

          {/* Empty state hint */}
          {stats && !stats.ready && (
            <p className="text-xs text-gray-600 italic">
              Ingest SOPs, manuals, or past reports to enable KB-grounded responses.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
