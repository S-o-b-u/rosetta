"use client";

import React, { useEffect, useState, useRef } from "react";
import { useMigration, type MigrationStatus } from "@/lib/migration";
import {
  IconBolt,
  IconCheck,
  IconX,
  IconLoader2,
  IconGitPullRequest,
} from "@tabler/icons-react";

/* ── Node display names ── */
const NODE_LABELS: Record<string, string> = {
  starting: "Initializing…",
  ast_context_node: "AST Parsing",
  discovery_agent: "Discovery",
  architecture_agent: "Architecture",
  validator: "Validation",
  wrapper: "Wrapping Up",
  done: "Complete",
};

const PIPELINE_NODES = [
  "ast_context_node",
  "discovery_agent",
  "architecture_agent",
  "validator",
];

/* ── Spring easing ── */
const SPRING = "cubic-bezier(0.34, 1.56, 0.64, 1)";

export function DynamicIsland() {
  const { state } = useMigration();
  const [expanded, setExpanded] = useState(false);
  const [visible, setVisible] = useState(true);
  const shrinkTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const status = state.status;
  const currentNode = state.currentNode;

  // Determine which node index we're at for progress
  const nodeIndex = PIPELINE_NODES.indexOf(currentNode ?? "");
  const progress =
    status === "completed"
      ? 100
      : status === "failed"
        ? 100
        : nodeIndex >= 0
          ? Math.round(((nodeIndex + 1) / PIPELINE_NODES.length) * 100)
          : 0;

  // Expand/shrink based on migration status
  useEffect(() => {
    if (shrinkTimer.current) {
      clearTimeout(shrinkTimer.current);
      shrinkTimer.current = null;
    }

    if (status === "running" || status === "connecting") {
      setExpanded(true);
      setVisible(true);
    } else if (status === "completed") {
      setExpanded(true);
      setVisible(true);
      shrinkTimer.current = setTimeout(() => setExpanded(false), 5000);
    } else if (status === "failed") {
      setExpanded(true);
      setVisible(true);
      shrinkTimer.current = setTimeout(() => setExpanded(false), 8000);
    } else {
      setExpanded(false);
    }

    return () => {
      if (shrinkTimer.current) clearTimeout(shrinkTimer.current);
    };
  }, [status]);

  const pillWidth = expanded
    ? status === "running"
      ? 440
      : 320
    : 180;

  const pillHeight = expanded
    ? status === "running"
      ? 72
      : 56
    : 36;

  return (
    <div
      className="absolute left-1/2 z-[60] flex items-start justify-center pointer-events-none"
      style={{
        top: 8, // align with menubar pills (pt-2 = 8px)
        transform: "translateX(-50%)",
      }}
    >
      <div
        onClick={() => {
          if (status === "completed" || status === "failed") {
            setExpanded((e) => !e);
          }
        }}
        className="pointer-events-auto overflow-hidden relative"
        style={{
          width: pillWidth,
          height: pillHeight,
          borderRadius: expanded ? 20 : 18,
          background: "rgba(0, 0, 0, 0.88)",
          backdropFilter: "blur(40px) saturate(180%)",
          WebkitBackdropFilter: "blur(40px) saturate(180%)",
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow: expanded
            ? "0 8px 40px rgba(0,0,0,0.6), 0 0 0 0.5px rgba(255,255,255,0.1) inset, 0 0 80px rgba(88,166,255,0.06)"
            : "0 4px 20px rgba(0,0,0,0.4), 0 0 0 0.5px rgba(255,255,255,0.08) inset",
          transition: `width 0.5s ${SPRING}, height 0.5s ${SPRING}, border-radius 0.5s ${SPRING}, box-shadow 0.4s ease`,
          cursor:
            status === "completed" || status === "failed"
              ? "pointer"
              : "default",
        }}
      >
        {/* Inner content — switches based on state */}
        <div
          className="absolute inset-0 flex items-center justify-center overflow-hidden"
          style={{
            transition: `opacity 0.3s ease`,
            opacity: 1,
          }}
        >
          {status === "idle" && <IdleContent />}
          {status === "connecting" && <ConnectingContent />}
          {status === "running" && (
            <RunningContent
              node={currentNode}
              progress={progress}
              retryCount={state.retryCount}
            />
          )}
          {status === "completed" && (
            <CompletedContent
              migrationId={state.migrationId}
              expanded={expanded}
            />
          )}
          {status === "failed" && (
            <FailedContent
              error={state.error}
              expanded={expanded}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════
   Sub-components for each island state
   ════════════════════════════════════════ */

function IdleContent() {
  return (
    <div className="flex items-center gap-2 px-4">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" />
        <span className="text-[12px] font-semibold tracking-wider text-zinc-200">
          ROSETTA
        </span>
      </div>
    </div>
  );
}

function ConnectingContent() {
  return (
    <div className="flex items-center gap-2.5 px-5">
      <IconLoader2
        size={16}
        className="text-blue-400 animate-spin"
      />
      <span className="text-[12px] font-medium text-zinc-300">
        Connecting to pipeline…
      </span>
    </div>
  );
}

function RunningContent({
  node,
  progress,
  retryCount,
}: {
  node: string | null;
  progress: number;
  retryCount: number;
}) {
  const label = NODE_LABELS[node ?? ""] ?? node ?? "…";

  return (
    <div className="flex flex-col justify-center w-full px-5 py-2.5 gap-2">
      {/* Top row: icon + stage name + retry badge */}
      <div className="flex items-center gap-2.5">
        <IconBolt
          size={16}
          className="text-blue-400 shrink-0"
          style={{
            filter: "drop-shadow(0 0 4px rgba(88,166,255,0.5))",
            animation: "pulse 2s ease-in-out infinite",
          }}
        />
        <span className="text-[13px] font-semibold text-white truncate">
          {label}
        </span>
        {retryCount > 1 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-yellow-500/20 text-yellow-400 border border-yellow-500/20 font-medium shrink-0">
            retry {retryCount}
          </span>
        )}
        <span className="text-[11px] text-zinc-500 ml-auto font-mono shrink-0">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-[3px] rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${progress}%`,
            background:
              "linear-gradient(90deg, #58a6ff 0%, #56d4dd 50%, #bc8cff 100%)",
            boxShadow: "0 0 8px rgba(88,166,255,0.4)",
            transition: `width 0.6s ${SPRING}`,
          }}
        />
      </div>

      {/* Bottom row */}
      <div className="flex items-center gap-2 text-[10px] text-zinc-500">
        <span>monolith → modern</span>
        <span className="ml-auto">
          {PIPELINE_NODES.indexOf(node ?? "") + 1}/{PIPELINE_NODES.length}
        </span>
      </div>
    </div>
  );
}

function CompletedContent({
  migrationId,
  expanded,
}: {
  migrationId: string | null;
  expanded: boolean;
}) {
  return (
    <div className="flex items-center gap-3 px-5">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{
          background: "rgba(59,185,80,0.15)",
          border: "1px solid rgba(59,185,80,0.3)",
        }}
      >
        <IconCheck size={14} className="text-green-400" />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[12px] font-semibold text-green-400">
          Migration Passed
        </span>
        {expanded && migrationId && (
          <span className="text-[10px] text-zinc-500 truncate">
            {migrationId}
          </span>
        )}
      </div>
      {expanded && (
        <div className="ml-auto flex items-center gap-1 shrink-0">
          <IconGitPullRequest size={13} className="text-zinc-500" />
          <span className="text-[10px] text-zinc-500">
            Ready for PR
          </span>
        </div>
      )}
    </div>
  );
}

function FailedContent({
  error,
  expanded,
}: {
  error: string | null;
  expanded: boolean;
}) {
  return (
    <div className="flex items-center gap-3 px-5">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{
          background: "rgba(248,81,73,0.15)",
          border: "1px solid rgba(248,81,73,0.3)",
        }}
      >
        <IconX size={14} className="text-red-400" />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[12px] font-semibold text-red-400">
          Migration Failed
        </span>
        {expanded && error && (
          <span className="text-[10px] text-zinc-500 truncate max-w-[200px]">
            {error.slice(0, 80)}
          </span>
        )}
      </div>
    </div>
  );
}
