"use client";

import { useState } from "react";
import TaskInput from "@/components/TaskInput";
import AgentLog from "@/components/AgentLog";
import OutputPanel from "@/components/OutputPanel";
import NetworkMonitor from "@/components/NetworkMonitor";
import { useAgentWebSocket } from "@/lib/websocket";

export default function Home() {
  const { events, connected, isRunning, sendTask } = useAgentWebSocket();
  const [uploadedFilePath, setUploadedFilePath] = useState<string | null>(null);

  const finishEvent = events.find((e) => e.type === "finish");

  const handleFileUpload = (filePath: string, _filename: string) => {
    setUploadedFilePath(filePath);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-950 text-white overflow-hidden">
      {/* ── Header ── */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-4 shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🛡</span>
          <div>
            <span className="text-blue-400 font-bold text-lg tracking-wide">
              SovereignForge
            </span>
            <p className="text-gray-600 text-xs">
              Sovereign On-Premise Agentic AI Workbench
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6 ml-auto text-xs text-gray-500">
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${
                connected ? "bg-green-400" : "bg-red-400"
              }`}
            />
            <span>{connected ? "Connected" : "Disconnected"}</span>
          </div>
          <div className="hidden md:flex items-center gap-1.5">
            <span className="text-green-400">●</span>
            <span>100% Local</span>
          </div>
          <div className="hidden md:flex items-center gap-1.5">
            <span className="text-blue-400">●</span>
            <span>Zero External Calls</span>
          </div>
        </div>
      </header>

      {/* ── Main 3-column layout ── */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-4 min-h-0">
        {/* Left: Task Input (3 cols) */}
        <div className="col-span-12 md:col-span-4 lg:col-span-3 overflow-y-auto">
          <TaskInput
            onSubmit={(input) => sendTask(input, uploadedFilePath ?? undefined)}
            onFileUpload={handleFileUpload}
            isRunning={isRunning}
          />
        </div>

        {/* Center: Agent Log (5 cols) */}
        <div className="col-span-12 md:col-span-4 lg:col-span-5 min-h-0">
          <AgentLog events={events} isRunning={isRunning} />
        </div>

        {/* Right: Output Panel (4 cols) */}
        <div className="col-span-12 md:col-span-4 lg:col-span-4 overflow-y-auto">
          <OutputPanel finishEvent={finishEvent} events={events} />
        </div>
      </div>

      {/* ── Bottom Network Monitor bar ── */}
      <footer className="h-14 bg-gray-900 border-t border-gray-800 shrink-0">
        <NetworkMonitor />
      </footer>
    </div>
  );
}
