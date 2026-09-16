"use client";

import { useNetworkMonitor, NetworkEntry } from "@/lib/websocket";

export default function NetworkMonitor() {
  const status = useNetworkMonitor();

  return (
    <div className="flex items-center gap-4 px-4 h-full overflow-hidden">
      {/* Sovereignty indicator */}
      <div className="flex items-center gap-2 shrink-0">
        <div
          className={`w-2.5 h-2.5 rounded-full ${
            status.sovereign ? "bg-green-400 animate-pulse" : "bg-red-500"
          }`}
        />
        <span
          className={`text-xs font-bold ${
            status.sovereign ? "text-green-400" : "text-red-400"
          }`}
        >
          {status.sovereign ? "SOVEREIGN" : "⚠️ BREACH DETECTED"}
        </span>
      </div>

      <div className="w-px h-6 bg-gray-800" />

      {/* Stats */}
      <div className="flex items-center gap-4 text-xs shrink-0">
        <span className="text-gray-500">
          Requests: <span className="text-gray-300">{status.total}</span>
        </span>
        <span
          className={status.external_blocked > 0 ? "text-red-400" : "text-gray-500"}
        >
          Blocked:{" "}
          <span className="font-bold">
            {status.external_blocked > 0 ? `⚠️ ${status.external_blocked}` : "0"}
          </span>
        </span>
      </div>

      <div className="w-px h-6 bg-gray-800" />

      {/* Recent entries ticker */}
      <div className="flex-1 overflow-hidden">
        <div className="flex items-center gap-2 overflow-x-auto pb-0.5 scrollbar-hide">
          {status.entries.length === 0 ? (
            <span className="text-gray-700 text-xs italic">
              Monitoring network... (start mitmproxy to see traffic)
            </span>
          ) : (
            [...status.entries].reverse().slice(0, 8).map((entry, i) => (
              <EntryPill key={i} entry={entry} />
            ))
          )}
        </div>
      </div>

      {/* Label */}
      <div className="shrink-0 text-xs text-gray-700">
        🛡 Network Monitor
      </div>
    </div>
  );
}

function EntryPill({ entry }: { entry: NetworkEntry }) {
  const isBlocked = entry.blocked;
  return (
    <div
      className={`shrink-0 flex items-center gap-1 px-2 py-0.5 rounded text-xs border ${
        isBlocked
          ? "bg-red-400/10 border-red-400/30 text-red-400"
          : "bg-green-400/10 border-green-400/20 text-green-400"
      }`}
      title={entry.url}
    >
      <span>{isBlocked ? "🚫" : "✓"}</span>
      <span className="font-mono">
        {entry.method} {entry.host}:{entry.port}
      </span>
    </div>
  );
}
