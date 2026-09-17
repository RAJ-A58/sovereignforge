"use client";

import { useEffect, useRef } from "react";
import { AgentEvent } from "@/lib/websocket";

interface AgentLogProps {
  events: AgentEvent[];
  isRunning: boolean;
}

// Color scheme per event type
const EVENT_STYLES: Record<string, { color: string; icon: string; label: string }> = {
  agent_start:    { color: "text-blue-400",    icon: "🚀", label: "START" },
  classified:     { color: "text-purple-400",  icon: "🏷️", label: "CLASSIFY" },
  thinking:       { color: "text-yellow-500",  icon: "💭", label: "THINKING" },
  thought:        { color: "text-yellow-300",  icon: "🧠", label: "THOUGHT" },
  tool_call:      { color: "text-orange-400",  icon: "🔧", label: "TOOL" },
  tool_result:    { color: "text-green-400",   icon: "✅", label: "RESULT" },
  finish:         { color: "text-emerald-400", icon: "🎯", label: "DONE" },
  error:          { color: "text-red-400",     icon: "❌", label: "ERROR" },
  max_iterations: { color: "text-red-300",     icon: "⏱️", label: "TIMEOUT" },
  streaming_thought: { color: "text-yellow-200",  icon: "✍️", label: "STREAMING" },
  guardrail_block:   { color: "text-red-500",     icon: "🛡️", label: "BLOCKED" },
};

function getEventContent(event: AgentEvent): string {
  const d = event.data as Record<string, unknown>;
  switch (event.type) {
    case "agent_start":
      return String(d.message ?? "");
    case "classified":
      return `${d.task_type} → ${d.model_key} model (${Math.round(Number(d.confidence) * 100)}% confidence) — ${d.reasoning}`;
    case "thinking":
      return String(d.message ?? "");
    case "thought":
      return `${d.thought}\n   → action: ${d.action}`;
    case "tool_call":
      return `${d.tool}(${JSON.stringify(d.input ?? {}).slice(0, 100)}${JSON.stringify(d.input ?? {}).length > 100 ? "..." : ""})`;
    case "tool_result": {
      const success = Boolean(d.success);
      const result = d.result as Record<string, unknown> | undefined;
      const elapsed = d.elapsed_s !== undefined ? ` (${d.elapsed_s}s)` : "";
      if (!success) {
        return `Failed — ${result?.error ?? "unknown error"}${elapsed}`;
      }
      // Show relevant result fields
      if (result?.filename) return `✓ Generated: ${result.filename}${elapsed}`;
      if (result?.stdout) return `✓ stdout: ${String(result.stdout).slice(0, 120)}${elapsed}`;
      if (result?.text) return `✓ Extracted ${String(result.text).length} chars${elapsed}`;
      if (result?.analysis) return `✓ Analysis: ${String(result.analysis).slice(0, 120)}${elapsed}`;
      if (result?.cache_hit) return `✓ Cache hit — instant${elapsed}`;
      return `✓ Success${elapsed}`;
    }
    case "finish":
      return String(d.answer ?? "Task complete");
    case "error":
      return String(d.message ?? "Unknown error");
    case "max_iterations":
      return String(d.message ?? "");
    case "streaming_thought":
      return String(d.text ?? "");
    case "guardrail_block":
      return `[${d.category}] ${d.message}`;
    default:
      return JSON.stringify(d).slice(0, 150);
  }
}

export default function AgentLog({ events, isRunning }: AgentLogProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 h-full flex flex-col">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2 shrink-0">
        <span className="font-semibold text-sm text-gray-200">Agent Execution Log</span>
        <span className="text-xs text-gray-600">({events.length} events)</span>
        {isRunning && (
          <span className="ml-auto flex items-center gap-1.5 text-yellow-400 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse inline-block" />
            Running...
          </span>
        )}
        {!isRunning && events.length > 0 && (
          <span className="ml-auto text-xs text-gray-600">Complete</span>
        )}
      </div>

      {/* Event list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-1 font-mono text-xs">
        {events.length === 0 ? (
          <p className="text-gray-700 italic pt-4 text-center">
            Waiting for task...
          </p>
        ) : (
          events.map((event, i) => {
            const style = EVENT_STYLES[event.type] ?? {
              color: "text-gray-400",
              icon: "•",
              label: event.type.toUpperCase(),
            };
            const content = getEventContent(event);

            return (
              <div key={i} className={`${style.color} leading-relaxed`}>
                <span className="mr-1.5">{style.icon}</span>
                <span className="text-gray-600 mr-1.5">[{style.label}]</span>
                <span className="whitespace-pre-wrap break-words">{content}</span>
                {event.type === "streaming_thought" && (
                  <span className="animate-pulse ml-0.5 text-yellow-300">▋</span>
                )}
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
