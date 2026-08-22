"use client";

import React, { useState } from "react";
import { useMigration } from "@/lib/migration";
import {
  IconChevronDown,
  IconChevronRight,
  IconCircleCheck,
  IconCircleDashed,
  IconBraces,
  IconArrowRight,
  IconFunction,
  IconAlertTriangle,
} from "@tabler/icons-react";

/* ── Colour palette ── */
const P = {
  bg: "#0d1117",
  sidebar: "#161b22",
  border: "#30363d",
  text: "#e6edf3",
  dim: "#484f58",
  blue: "#58a6ff",
  cyan: "#56d4dd",
  green: "#3fb950",
  red: "#f85149",
  purple: "#bc8cff",
  yellow: "#d29922",
  orange: "#f0883e",
};

/* ──────────────────────────────────────────────────
   Collapsible section with indent lines
   ────────────────────────────────────────────────── */
function TreeSection({
  title,
  icon,
  color,
  badge,
  defaultOpen = false,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  color: string;
  badge?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full px-3 py-2 hover:bg-white/5 transition-colors text-left"
      >
        {open ? (
          <IconChevronDown size={14} style={{ color }} />
        ) : (
          <IconChevronRight size={14} style={{ color }} />
        )}
        <span style={{ color }}>{icon}</span>
        <span className="text-[13px] font-medium" style={{ color: P.text }}>
          {title}
        </span>
        {badge && (
          <span
            className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-medium"
            style={{ background: color + "22", color }}
          >
            {badge}
          </span>
        )}
      </button>
      {open && (
        <div className="ml-6 border-l" style={{ borderColor: P.border }}>
          {children}
        </div>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────
   A single key-value leaf in the tree
   ────────────────────────────────────────────────── */
function Leaf({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-start gap-2 px-3 py-1 text-[12px] hover:bg-white/[0.03] group">
      <span style={{ color: P.dim }}>{label}:</span>
      <span className="break-all" style={{ color: color ?? P.text }}>
        {value}
      </span>
    </div>
  );
}

/* ──────────────────────────────────────────────────
   Node card (for graph nodes)
   ────────────────────────────────────────────────── */
function NodeRow({
  id,
  label,
  isTarget,
}: {
  id: string;
  label: string;
  isTarget?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-[12px] hover:bg-white/[0.04] rounded mx-1">
      <div
        className="w-2 h-2 rounded-full shrink-0"
        style={{ background: isTarget ? P.blue : P.cyan }}
      />
      <span style={{ color: P.text }} className="font-medium">
        {id}
      </span>
      <span
        className="text-[10px] px-1.5 rounded"
        style={{ background: P.border, color: P.dim }}
      >
        {label}
      </span>
      {isTarget && (
        <span className="text-[10px] ml-auto" style={{ color: P.blue }}>
          target
        </span>
      )}
    </div>
  );
}

/* ──────────────────────────────────────────────────
   Edge row
   ────────────────────────────────────────────────── */
function EdgeRow({
  source,
  target,
  label,
}: {
  source: string;
  target: string;
  label: string;
}) {
  return (
    <div className="flex items-center gap-2 px-3 py-1 text-[12px] hover:bg-white/[0.04] rounded mx-1">
      <span style={{ color: P.cyan }}>{source}</span>
      <IconArrowRight size={12} style={{ color: P.dim }} />
      <span style={{ color: P.purple }}>{target}</span>
      <span
        className="ml-auto text-[10px] px-1.5 rounded"
        style={{ background: P.border, color: P.dim }}
      >
        {label}
      </span>
    </div>
  );
}

/* ──────────────────────────────────────────────────
   Pipeline stage indicator
   ────────────────────────────────────────────────── */
function StageIndicator({ name, active }: { name: string; active: boolean }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1.5 text-[12px]">
      {active ? (
        <IconCircleCheck size={14} style={{ color: P.green }} />
      ) : (
        <IconCircleDashed size={14} style={{ color: P.dim }} />
      )}
      <span style={{ color: active ? P.text : P.dim }}>{name}</span>
    </div>
  );
}

/* ══════════════════════════════════════════════════
   Main AST Explorer component
   ══════════════════════════════════════════════════ */
export function AstApp() {
  const { state } = useMigration();
  const {
    neo4jContext,
    discoveryData,
    architectureData,
    validatorData,
    parityReport,
  } = state;

  const nodes = neo4jContext?.nodes ?? [];
  const edges = neo4jContext?.edges ?? [];
  const targetId = edges.length > 0 ? edges[0].source : nodes[0]?.id;

  const formulaIr = discoveryData
    ? (discoveryData as any).formula_ir
    : null;
  const testCases = discoveryData
    ? (discoveryData as any).test_cases
    : null;

  return (
    <div
      className="flex h-full font-mono text-[13px] overflow-hidden select-text"
      style={{ background: P.bg, color: P.text }}
    >
      {/* ── Left: Tree ── */}
      <div
        className="w-[300px] shrink-0 flex flex-col overflow-hidden"
        style={{ background: P.sidebar, borderRight: `1px solid ${P.border}` }}
      >
        {/* header */}
        <div
          className="px-3 py-2 text-[11px] font-semibold uppercase tracking-widest shrink-0"
          style={{ color: P.dim, borderBottom: `1px solid ${P.border}` }}
        >
          Explorer
        </div>

        {/* pipeline stages */}
        <div className="py-2" style={{ borderBottom: `1px solid ${P.border}` }}>
          <StageIndicator name="AST / Neo4j" active={!!neo4jContext} />
          <StageIndicator name="Discovery" active={!!discoveryData} />
          <StageIndicator name="Architecture" active={!!architectureData} />
          <StageIndicator name="Validator" active={!!validatorData} />
        </div>

        {/* tree content */}
        <div className="flex-1 overflow-auto py-1">
          {nodes.length > 0 && (
            <TreeSection
              title="Service Nodes"
              icon={<IconBraces size={14} />}
              color={P.cyan}
              badge={`${nodes.length}`}
              defaultOpen
            >
              {nodes.map((n) => (
                <NodeRow
                  key={n.id}
                  id={n.id}
                  label={n.label}
                  isTarget={n.id === targetId}
                />
              ))}
            </TreeSection>
          )}

          {edges.length > 0 && (
            <TreeSection
              title="CALLS Edges"
              icon={<IconArrowRight size={14} />}
              color={P.purple}
              badge={`${edges.length}`}
              defaultOpen
            >
              {edges.map((e, i) => (
                <EdgeRow
                  key={i}
                  source={e.source}
                  target={e.target}
                  label={e.label}
                />
              ))}
            </TreeSection>
          )}

          {formulaIr && (
            <TreeSection
              title="Formula IR"
              icon={<IconFunction size={14} />}
              color={P.blue}
              defaultOpen
            >
              <Leaf label="method" value={formulaIr.method_name} color={P.cyan} />
              <Leaf label="formula" value={formulaIr.formula} color={P.green} />
              {(formulaIr.formula_terms ?? []).map((t: any, i: number) => (
                <Leaf
                  key={i}
                  label={`  term[${i}]`}
                  value={`${t.name} ← ${t.source_method}`}
                  color={P.purple}
                />
              ))}
            </TreeSection>
          )}

          {testCases && (
            <TreeSection
              title="Test Cases"
              icon={<IconBraces size={14} />}
              color={P.yellow}
              badge={`${testCases.length}`}
            >
              {testCases.map((tc: any, i: number) => (
                <Leaf
                  key={i}
                  label={tc.name}
                  value={`expected: ${JSON.stringify(tc.expected_output)}`}
                  color={P.yellow}
                />
              ))}
            </TreeSection>
          )}

          {parityReport && (
            <TreeSection
              title="Validation Report"
              icon={
                parityReport.overall_passed ? (
                  <IconCircleCheck size={14} />
                ) : (
                  <IconAlertTriangle size={14} />
                )
              }
              color={parityReport.overall_passed ? P.green : P.red}
              badge={`${parityReport.tiers_passed}/${parityReport.tiers_total}`}
              defaultOpen
            >
              {parityReport.tiers.map((t, i) => (
                <Leaf
                  key={i}
                  label={t.tier}
                  value={t.passed ? "PASS" : "FAIL"}
                  color={t.passed ? P.green : P.red}
                />
              ))}
            </TreeSection>
          )}

          {nodes.length === 0 && !discoveryData && (
            <div
              className="px-4 py-8 text-center text-[12px]"
              style={{ color: P.dim }}
            >
              Run a migration to populate the AST tree.
            </div>
          )}
        </div>
      </div>

      {/* ── Right: Detail Panel ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* header */}
        <div
          className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest shrink-0 flex items-center gap-2"
          style={{ color: P.dim, borderBottom: `1px solid ${P.border}` }}
        >
          <IconBraces size={13} style={{ color: P.blue }} />
          Generated Python
        </div>

        {/* code view */}
        <div className="flex-1 overflow-auto px-4 py-3">
          {architectureData ? (
            <pre
              className="text-[12px] leading-[1.7] whitespace-pre-wrap"
              style={{ color: P.green }}
            >
              {(architectureData as any).generated_python ??
                (architectureData as any).pure_function_source ??
                "No source available."}
            </pre>
          ) : (
            <div
              className="flex items-center justify-center h-full text-[12px]"
              style={{ color: P.dim }}
            >
              Generated code will appear after the Architecture agent runs.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
