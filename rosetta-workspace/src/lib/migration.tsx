"use client";

import React, { createContext, useContext, useState, useCallback, useRef } from "react";

// ── Types derived from the real backend SSE events ──

export interface GraphNode {
  id: string;
  label: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  action: string | null;
}

export interface Neo4jContext {
  migration_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface ParityTier {
  tier: string;
  passed: boolean;
  feedback: string;
  details?: Record<string, unknown>;
}

export interface ParityReport {
  method: string;
  baseline_mode: string;
  overall_passed: boolean;
  tiers_passed: number;
  tiers_total: number;
  summary: string;
  tiers: ParityTier[];
}

export interface MigrationEvent {
  id: number;
  timestamp: string;
  event: string;
  node?: string;
  data: Record<string, unknown>;
}

export type MigrationStatus =
  | "idle"
  | "connecting"
  | "running"
  | "completed"
  | "failed";

export interface MigrationState {
  status: MigrationStatus;
  migrationId: string | null;
  events: MigrationEvent[];
  neo4jContext: Neo4jContext | null;
  discoveryData: Record<string, unknown> | null;
  architectureData: Record<string, unknown> | null;
  validatorData: Record<string, unknown> | null;
  parityReport: ParityReport | null;
  error: string | null;
  currentNode: string | null;
  retryCount: number;
}

interface MigrationContextValue {
  state: MigrationState;
  startMigration: (filePath: string, targetMethod: string) => void;
}

const MigrationContext = createContext<MigrationContextValue | null>(null);

export function useMigration(): MigrationContextValue {
  const ctx = useContext(MigrationContext);
  if (!ctx)
    throw new Error("useMigration must be used within MigrationProvider");
  return ctx;
}

const INITIAL_STATE: MigrationState = {
  status: "idle",
  migrationId: null,
  events: [],
  neo4jContext: null,
  discoveryData: null,
  architectureData: null,
  validatorData: null,
  parityReport: null,
  error: null,
  currentNode: null,
  retryCount: 0,
};

const API_BASE = "http://localhost:8000";

export function MigrationProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<MigrationState>(INITIAL_STATE);
  const eventCounter = useRef(0);

  const addEvent = useCallback(
    (event: string, node: string | undefined, data: Record<string, unknown>) => {
      eventCounter.current += 1;
      const evt: MigrationEvent = {
        id: eventCounter.current,
        timestamp: new Date().toISOString(),
        event,
        node,
        data,
      };
      setState((prev) => ({ ...prev, events: [...prev.events, evt] }));
    },
    []
  );

  const startMigration = useCallback(
    (filePath: string, targetMethod: string) => {
      // Reset state
      eventCounter.current = 0;
      setState({
        ...INITIAL_STATE,
        status: "connecting",
      });

      const doStream = async () => {
        try {
          const resp = await fetch(`${API_BASE}/api/migrate/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              file_path: filePath,
              target_method: targetMethod,
            }),
          });

          if (!resp.ok || !resp.body) {
            setState((prev) => ({
              ...prev,
              status: "failed",
              error: `HTTP ${resp.status}: ${resp.statusText}`,
            }));
            return;
          }

          setState((prev) => ({ ...prev, status: "running" }));

          const reader = resp.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE frames from buffer
            const frames = buffer.split("\n\n");
            buffer = frames.pop() || ""; // last incomplete frame stays in buffer

            for (const frame of frames) {
              if (!frame.trim()) continue;

              let eventType = "message";
              let dataStr = "";

              for (const line of frame.split("\n")) {
                if (line.startsWith("event: ")) {
                  eventType = line.slice(7).trim();
                } else if (line.startsWith("data: ")) {
                  dataStr = line.slice(6);
                }
              }

              if (!dataStr) continue;

              try {
                const payload = JSON.parse(dataStr);

                // ── Handle each event type ──
                if (eventType === "migration_started") {
                  setState((prev) => ({
                    ...prev,
                    migrationId: payload.migration_id,
                    currentNode: "starting",
                  }));
                  addEvent("migration_started", undefined, payload);
                } else if (eventType === "node") {
                  const nodeName = payload.node as string;
                  const nodeState = payload.state || {};

                  addEvent("node", nodeName, payload);

                  setState((prev) => {
                    const updates: Partial<MigrationState> = {
                      currentNode: nodeName,
                    };

                    if (nodeName === "ast_context_node" && nodeState.neo4j_context) {
                      updates.neo4jContext = nodeState.neo4j_context as Neo4jContext;
                    }

                    if (nodeName === "discovery_agent") {
                      updates.discoveryData = nodeState;
                    }

                    if (nodeName === "architecture_agent") {
                      updates.architectureData = nodeState;
                      if (typeof nodeState.retry_count === "number") {
                        updates.retryCount = nodeState.retry_count;
                      }
                    }

                    if (nodeName === "validator") {
                      updates.validatorData = nodeState;
                      if (nodeState.parity_report) {
                        updates.parityReport = nodeState.parity_report as ParityReport;
                      }
                    }

                    if (nodeName === "wrapper") {
                      updates.status = "completed";
                    }

                    return { ...prev, ...updates };
                  });
                } else if (eventType === "migration_completed") {
                  setState((prev) => ({
                    ...prev,
                    status: "completed",
                    currentNode: "done",
                  }));
                  addEvent("migration_completed", undefined, payload);
                } else if (eventType === "error") {
                  setState((prev) => ({
                    ...prev,
                    status: "failed",
                    error: payload.error || "Unknown pipeline error",
                  }));
                  addEvent("error", undefined, payload);
                } else if (eventType === "stream_end") {
                  setState((prev) => ({
                    ...prev,
                    status: prev.status === "running" ? "failed" : prev.status,
                    currentNode: "done",
                  }));
                  addEvent("stream_end", undefined, payload);
                }
              } catch {
                // Skip malformed JSON frames
              }
            }
          }
        } catch (err: unknown) {
          const message = err instanceof Error ? err.message : String(err);
          setState((prev) => ({
            ...prev,
            status: "failed",
            error: `Connection error: ${message}`,
          }));
        }
      };

      doStream();
    },
    [addEvent]
  );

  return (
    <MigrationContext.Provider value={{ state, startMigration }}>
      {children}
    </MigrationContext.Provider>
  );
}
