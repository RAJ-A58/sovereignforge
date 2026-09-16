// frontend/lib/websocket.ts
// WebSocket client hook for SovereignForge agent communication

import { useEffect, useRef, useState, useCallback } from "react";

export interface AgentEvent {
  type: string;
  data: Record<string, unknown>;
}

export function useAgentWebSocket(backendUrl = "ws://localhost:8000") {
  const wsRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${backendUrl}/ws/agent`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onclose = () => {
      setConnected(false);
      setIsRunning(false);
      // Auto-reconnect after 3 seconds
      setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    ws.onmessage = (msg: MessageEvent) => {
      try {
        const event: AgentEvent = JSON.parse(msg.data);
        setEvents((prev) => [...prev, event]);

        if (
          event.type === "finish" ||
          event.type === "error" ||
          event.type === "max_iterations"
        ) {
          setIsRunning(false);
        }
      } catch {
        console.error("Failed to parse WebSocket message:", msg.data);
      }
    };
  }, [backendUrl]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const sendTask = useCallback(
    (userInput: string, filePath?: string) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.error("WebSocket not connected");
        return;
      }
      setEvents([]);
      setIsRunning(true);
      wsRef.current.send(
        JSON.stringify({
          user_input: userInput,
          file_path: filePath ?? null,
        })
      );
    },
    []
  );

  return { events, connected, isRunning, sendTask };
}

// ── Network Monitor WebSocket Hook ──
export interface NetworkEntry {
  timestamp: string;
  method: string;
  host: string;
  port: number;
  url: string;
  is_local: boolean;
  blocked: boolean;
}

export interface NetworkStatus {
  entries: NetworkEntry[];
  total: number;
  external_blocked: number;
  sovereign: boolean;
}

export function useNetworkMonitor(backendUrl = "ws://localhost:8000") {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<NetworkStatus>({
    entries: [],
    total: 0,
    external_blocked: 0,
    sovereign: true,
  });

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(`${backendUrl}/ws/network`);
      wsRef.current = ws;

      ws.onmessage = (msg: MessageEvent) => {
        try {
          setStatus(JSON.parse(msg.data));
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => wsRef.current?.close();
  }, [backendUrl]);

  return status;
}
