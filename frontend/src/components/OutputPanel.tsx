"use client";

import { AgentEvent } from "@/lib/websocket";

interface OutputPanelProps {
  finishEvent: AgentEvent | undefined;
  events: AgentEvent[];
}

export default function OutputPanel({ finishEvent, events }: OutputPanelProps) {
  const hasError = events.some((e) => e.type === "error");
  const isRunning = events.length > 0 && !finishEvent && !hasError;

  // Extract generated files from tool_result events
  const generatedFiles: string[] = [];
  for (const event of events) {
    if (event.type === "tool_result") {
      const result = event.data?.result as Record<string, unknown> | undefined;
      if (result?.filename && typeof result.filename === "string") {
        generatedFiles.push(result.filename);
      }
    }
  }

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 shrink-0">
        <span className="font-semibold text-sm text-gray-200">Output</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {/* Empty state */}
        {events.length === 0 && (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-gray-700 italic text-sm text-center">
              Agent output will appear here
            </p>
          </div>
        )}

        {/* Running indicator */}
        {isRunning && (
          <div className="flex items-center gap-3 p-3 bg-yellow-400/5 border border-yellow-400/20 rounded-lg">
            <span className="text-yellow-400 text-xl animate-spin">⟳</span>
            <span className="text-yellow-400 text-sm">Agent is working...</span>
          </div>
        )}

        {/* Final answer */}
        {finishEvent && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-emerald-400 text-lg">🎯</span>
              <span className="text-emerald-400 font-semibold text-sm">Task Complete</span>
            </div>

            <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <p className="text-gray-200 text-sm whitespace-pre-wrap leading-relaxed">
                {String(finishEvent.data?.answer ?? "Task complete.")}
              </p>
            </div>

            {/* Artifacts listed in finish event */}
            {Array.isArray(finishEvent.data?.artifacts) &&
              (finishEvent.data.artifacts as string[]).length > 0 && (
                <ArtifactList
                  files={finishEvent.data.artifacts as string[]}
                />
              )}
          </div>
        )}

        {/* Generated files (from tool_result events) */}
        {generatedFiles.length > 0 && (
          <ArtifactList files={generatedFiles} />
        )}

        {/* Error state */}
        {hasError && !finishEvent && (
          <div className="p-3 bg-red-400/5 border border-red-400/20 rounded-lg">
            <p className="text-red-400 text-sm font-semibold mb-1">❌ Error</p>
            {events
              .filter((e) => e.type === "error")
              .map((e, i) => (
                <p key={i} className="text-red-300 text-xs">
                  {String(e.data?.message ?? "Unknown error")}
                </p>
              ))}
          </div>
        )}

        {/* Task Classification badge */}
        {events.find((e) => e.type === "classified") && (
          <ClassificationBadge
            event={events.find((e) => e.type === "classified")!}
          />
        )}
      </div>
    </div>
  );
}

function ArtifactList({ files }: { files: string[] }) {
  return (
    <div className="space-y-2">
      <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide">
        Generated Files
      </p>
      {files.map((filename, i) => (
        <a
          key={i}
          href={`http://localhost:8000/download/${filename}`}
          download={filename}
          className="flex items-center gap-2 p-2 bg-blue-500/10 border border-blue-500/20 
                     rounded-lg text-blue-400 text-xs hover:bg-blue-500/20 transition"
        >
          <span>📄</span>
          <span className="flex-1 truncate">{filename}</span>
          <span className="text-blue-600">↓ Download</span>
        </a>
      ))}
    </div>
  );
}

function ClassificationBadge({ event }: { event: AgentEvent }) {
  const { task_type, model_key, confidence } = event.data as Record<string, unknown>;
  const typeColors: Record<string, string> = {
    document: "text-blue-400 bg-blue-400/10 border-blue-400/20",
    coding: "text-orange-400 bg-orange-400/10 border-orange-400/20",
    multimodal: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  };
  const color = typeColors[String(task_type)] ?? "text-gray-400 bg-gray-800 border-gray-700";

  return (
    <div className={`inline-flex items-center gap-2 px-2 py-1 rounded border text-xs ${color}`}>
      <span>🏷️</span>
      <span className="font-medium capitalize">{String(task_type)}</span>
      <span className="text-gray-500">·</span>
      <span>{String(model_key)} model</span>
      <span className="text-gray-500">·</span>
      <span>{Math.round(Number(confidence) * 100)}% confidence</span>
    </div>
  );
}
