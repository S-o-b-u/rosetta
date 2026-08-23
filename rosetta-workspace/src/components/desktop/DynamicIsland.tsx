"use client";

import React, { useEffect, useState, useRef } from "react";
import { useMigration, type MigrationStatus } from "@/lib/migration";
import { LiquidGlassCard } from "@/components/ui/liquid-glass";
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
      ? 460
      : 340
    : 190;

  const pillHeight = expanded
    ? status === "running"
      ? 78
      : 62
    : 38;

  return (
    <div
      className="absolute left-1/2 z-[60] flex items-start justify-center pointer-events-none"
      style={{
        top: 8,
        transform: "translateX(-50%)",
      }}
    >
      <LiquidGlassCard
        draggable={false}
        expandable={false}
        blurIntensity="xl"
        glowIntensity="xs"
        shadowIntensity="xs"
        borderRadius={expanded ? '22px' : '999px'}
        className="pointer-events-auto overflow-hidden relative"
        style={{
          width: pillWidth,
          height: pillHeight,
          transition: `width 0.5s ${SPRING}, height 0.5s ${SPRING}, border-radius 0.5s ${SPRING}`,
          cursor:
            status === "completed" || status === "failed"
              ? "pointer"
              : "default",
          background: 'rgba(10,10,10,0.75)',
          border: '1px solid rgba(255,255,255,0.1)',
        }}
        onClick={() => {
          if (status === "completed" || status === "failed") {
            setExpanded((e) => !e);
          }
        }}
      >
        {/* Inner content — switches based on state */}
        <div
          className="absolute inset-0 flex items-center justify-center overflow-hidden z-30"
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
      </LiquidGlassCard>
    </div>
  );
}

/* ════════════════════════════════════════
   Sub-components for each island state
   ════════════════════════════════════════ */

function IdleContent() {
  return (
    <div className="flex items-center gap-2.5 px-5 py-2">
      <span className="text-[12px] font-bold tracking-widest text-white">
        RECAST
      </span>
    </div>
  );
}

function ConnectingContent() {
  return (
    <div className="flex items-center gap-3 px-5 py-2">
      <IconLoader2 size={15} className="text-white animate-spin" />
      <span className="text-[12px] font-bold tracking-wide text-white uppercase">
        Connecting
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
      {/* Top row */}
      <div className="flex items-center gap-2.5">
        <span className="text-[13px] font-bold text-white truncate uppercase tracking-wide">
          {label}
        </span>
        {retryCount > 1 && (
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-white text-black font-bold shrink-0">
            RETRY {retryCount}
          </span>
        )}
        <span className="text-[11px] text-zinc-400 ml-auto font-mono shrink-0">
          {progress}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-[3px] rounded-none bg-[#262626] overflow-hidden">
        <div
          className="h-full bg-white"
          style={{
            width: `${progress}%`,
            transition: `width 0.6s ${SPRING}`,
          }}
        />
      </div>

      {/* Bottom row */}
      <div className="flex items-center gap-2 text-[10px] text-zinc-500 uppercase tracking-widest font-semibold">
        <span>Monolith to Modern</span>
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
    <div className="flex items-center gap-3 px-5 py-3 w-full">
      <div className="w-6 h-6 flex items-center justify-center shrink-0 bg-white text-black rounded-sm">
        <IconCheck size={14} stroke={3} />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[12px] font-bold text-white uppercase tracking-wide">
          Migration Passed
        </span>
        {expanded && migrationId && (
          <span className="text-[10px] text-zinc-400 truncate">
            {migrationId}
          </span>
        )}
      </div>
      {expanded && (
        <div className="ml-auto flex items-center gap-1.5 shrink-0 border-l border-[#262626] pl-3">
          <IconGitPullRequest size={14} className="text-white" />
          <span className="text-[10px] text-white font-bold tracking-wide uppercase">
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
    <div className="flex items-center gap-3 px-5 py-3 w-full">
      <div className="w-6 h-6 flex items-center justify-center shrink-0 bg-white text-black rounded-sm">
        <IconX size={14} stroke={3} />
      </div>
      <div className="flex flex-col min-w-0">
        <span className="text-[12px] font-bold text-white uppercase tracking-wide">
          Migration Failed
        </span>
        {expanded && error && (
          <span className="text-[10px] text-zinc-400 truncate max-w-[200px]">
            {error.slice(0, 80)}
          </span>
        )}
      </div>
    </div>
  );
}
