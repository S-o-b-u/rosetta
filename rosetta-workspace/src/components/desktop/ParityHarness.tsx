"use client";

import React, { useState } from "react";
import { useMigration } from "@/lib/migration";
import type { ParityTier } from "@/lib/migration";

/* ── Flat design system (high contrast) ── */
const T = {
  bg:      "#0d1117",
  surface: "#161b22",
  surface2:"#21262d",
  border:  "#30363d",
  text:    "#f0f6fc",
  dim:     "#8b949e",
  muted:   "#484f58",
  blue:    "#58a6ff",
  green:   "#3fb950",
  red:     "#f85149",
  amber:   "#d29922",
};

/* ── Status badge ── */
function StatusBadge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="text-[10px] px-2 py-0.5 rounded font-medium"
      style={{ background: color + "18", color }}
    >
      {label}
    </span>
  );
}

/* ── Collapsible tier row ── */
function TierRow({ tier }: { tier: ParityTier & { status?: string } }) {
  const [open, setOpen] = useState(false);

  const isSkipped = tier.status === "superseded" || tier.status === "not_applicable";
  const color = isSkipped ? T.dim : tier.passed ? T.green : T.red;
  const label = isSkipped ? "skipped" : tier.passed ? "pass" : "fail";

  const tierNames: Record<string, string> = {
    T1_formula_completeness:    "T1 — Formula Completeness",
    T3_golden_file_equivalence: "T3 — Golden File",
    shadow_validation:          "Shadow — LLM Fixture",
  };

  const displayName = tierNames[tier.tier] ?? tier.tier.replace(/_/g, " ");

  return (
    <div style={{ borderBottom: `1px solid ${T.border}` }}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 w-full px-4 py-3 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: color }} />
        <span className="flex-1 text-[12px] font-medium" style={{ color: T.text }}>
          {displayName}
        </span>
        <StatusBadge label={label} color={color} />
        <svg
          width="12" height="12" viewBox="0 0 12 12" fill="none"
          className="shrink-0 transition-transform"
          style={{ transform: open ? "rotate(180deg)" : "rotate(0deg)", color: T.muted }}
        >
          <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-0">
          <pre
            className="text-[10px] font-mono leading-relaxed whitespace-pre-wrap"
            style={{ color: T.dim }}
          >
            {tier.feedback}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ── Fixture case row ── */
function FixtureRow({ fixture }: { fixture: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const passed = Boolean(fixture.passed);
  const id = String(fixture.fixture_id ?? fixture.name ?? "case");
  const desc = fixture.description ? String(fixture.description) : null;
  const diffs = Array.isArray(fixture.differences) ? fixture.differences as string[] : [];
  const trace = fixture.arithmetic_trace as Record<string, string> | null;

  return (
    <div style={{ borderBottom: `1px solid ${T.border}` }}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-3 w-full px-4 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: passed ? T.green : T.red }} />
        <span className="flex-1 text-[11px] font-mono" style={{ color: T.text }}>{id}</span>
        {desc && <span className="text-[10px] truncate max-w-[180px] hidden sm:block" style={{ color: T.dim }}>{desc}</span>}
        <StatusBadge label={passed ? "match" : "diff"} color={passed ? T.green : T.red} />
      </button>
      {open && (
        <div className="px-4 pb-3" style={{ borderTop: `1px solid ${T.border}` }}>
          {!passed && diffs.length > 0 && (
            <div className="pt-2 space-y-1">
              {diffs.map((d, i) => (
                <div key={i} className="text-[10px] font-mono pl-3" style={{ color: T.red, borderLeft: `2px solid ${T.red}` }}>
                  {d}
                </div>
              ))}
            </div>
          )}
          {passed && trace && (
            <div className="pt-2">
              <div className="text-[10px] mb-1.5 uppercase tracking-widest" style={{ color: T.muted }}>
                Arithmetic trace
              </div>
              <div className="space-y-1">
                {Object.entries(trace).map(([k, v]) => (
                  <div key={k} className="flex gap-4 text-[10px] font-mono">
                    <span className="w-36 shrink-0 truncate" style={{ color: T.dim }}>{k}</span>
                    <span style={{ color: T.text }}>{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════
   PARITY HARNESS
   ══════════════════════════════════════════════════ */
export function ParityHarness() {
  const { state } = useMigration();
  const [tab, setTab] = useState<"tiers" | "code" | "diff">("tiers");

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const arch = state.architectureData as any;
  const candidateSource: string =
    arch?.pure_function_source ?? arch?.candidate_source ?? arch?.generated_python ?? "";

  const parityReport = state.parityReport;
  const tiers = parityReport?.tiers ?? [];
  const t3Tier = tiers.find(t => t.tier === "T3_golden_file_equivalence");
  const fixtureCases = (t3Tier?.details as { cases?: Record<string, unknown>[] } | undefined)?.cases ?? [];

  const tabs = [
    { id: "tiers" as const, label: "Tier Results" },
    { id: "code"  as const, label: "Code" },
    { id: "diff"  as const, label: "Fixture Diff" },
  ];

  const overallColor = !parityReport ? T.dim : parityReport.overall_passed ? T.green : T.red;
  const overallLabel = !parityReport ? "" : parityReport.overall_passed ? "PASS" : "FAIL";

  return (
    <div className="flex flex-col h-full text-[12px] overflow-hidden" style={{ background: T.bg, color: T.text }}>

      {/* Header */}
      <div
        className="px-4 py-2.5 flex items-center gap-3 shrink-0"
        style={{ borderBottom: `1px solid ${T.border}` }}
      >
        <span className="text-[11px] font-semibold" style={{ color: T.dim }}>PARITY HARNESS</span>
        {parityReport && (
          <div className="ml-auto flex items-center gap-2">
            <span className="text-[11px] font-medium" style={{ color: overallColor }}>
              {overallLabel}
            </span>
            <span className="text-[10px]" style={{ color: T.dim }}>
              {parityReport.tiers_passed}/{parityReport.tiers_total} tiers
            </span>
          </div>
        )}
        {!parityReport && (
          <span className="ml-auto text-[10px]" style={{ color: T.muted }}>Awaiting migration</span>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex shrink-0" style={{ borderBottom: `1px solid ${T.border}`, background: T.surface }}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="px-4 py-2 text-[11px] font-medium transition-colors relative"
            style={{ color: tab === t.id ? T.text : T.dim }}
          >
            {tab === t.id && (
              <div
                className="absolute bottom-0 left-0 right-0 h-[1px]"
                style={{ background: T.blue }}
              />
            )}
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">

        {/* ── Tiers tab ── */}
        {tab === "tiers" && (
          <div>
            {tiers.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-[11px]" style={{ color: T.muted }}>
                No results yet — run a migration first.
              </div>
            ) : (
              tiers.map((tier, i) => (
                <TierRow key={i} tier={tier as ParityTier & { status?: string }} />
              ))
            )}
          </div>
        )}

        {/* ── Code tab ── */}
        {tab === "code" && (
          <div className="flex h-full">
            {/* Java side */}
            <div className="w-[40%] flex flex-col" style={{ borderRight: `1px solid ${T.border}` }}>
              <div
                className="px-3 py-2 flex items-center gap-2 shrink-0"
                style={{ borderBottom: `1px solid ${T.border}`, background: T.surface }}
              >
                <span className="text-[10px] font-medium" style={{ color: T.dim }}>LEGACY JAVA</span>
                <span className="ml-auto text-[10px]" style={{ color: T.muted }}>ShoppingCart.java</span>
              </div>
              <div className="flex-1 overflow-auto p-4 text-[11px] font-mono leading-relaxed" style={{ color: T.dim }}>
                <div style={{ color: T.muted }} className="mb-2">{"// getGrandTotal()"}</div>
                <div>
                  <span style={{ color: T.text }}>{"public BigDecimal getGrandTotal() {"}</span>
                </div>
                <div className="pl-4 mt-1">
                  <div style={{ color: T.text }}>{"return getSubTotal()"}</div>
                  {["getTotalShipping()", "getTotalSalesTax()", "getOrderOtherAdjustmentTotal()", "getOrderGlobalAdjustments()"].map(m => (
                    <div key={m} style={{ color: T.dim }}>{`.add(${m})`}</div>
                  ))}
                </div>
                <div style={{ color: T.text }}>{"}"}</div>
                <div className="mt-4 pt-3" style={{ borderTop: `1px solid ${T.border}` }}>
                  <div className="text-[9px] uppercase tracking-widest mb-2" style={{ color: T.muted }}>
                    AST Dependencies
                  </div>
                  {["getSubTotal", "getTotalShipping", "getTotalSalesTax", "getOrderOtherAdjustmentTotal", "getOrderGlobalAdjustments"].map(m => (
                    <div key={m} className="flex items-center gap-2 py-0.5">
                      <div className="w-1 h-1 rounded-full" style={{ background: T.muted }} />
                      <span style={{ color: T.dim }}>{m}()</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Python side */}
            <div className="flex-1 flex flex-col">
              <div
                className="px-3 py-2 flex items-center gap-2 shrink-0"
                style={{ borderBottom: `1px solid ${T.border}`, background: T.surface }}
              >
                <span className="text-[10px] font-medium" style={{ color: T.dim }}>GENERATED PYTHON</span>
                {parityReport?.overall_passed && (
                  <span className="ml-auto">
                    <StatusBadge label="certified" color={T.green} />
                  </span>
                )}
              </div>
              <div className="flex-1 overflow-auto p-4">
                {candidateSource ? (
                  <pre className="text-[11px] font-mono leading-relaxed whitespace-pre-wrap" style={{ color: "#a8c4a2" }}>
                    {candidateSource}
                  </pre>
                ) : (
                  <div className="flex items-center justify-center h-full text-[11px]" style={{ color: T.muted }}>
                    Generated Python will appear after migration.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Diff tab ── */}
        {tab === "diff" && (
          <div>
            {fixtureCases.length === 0 ? (
              <div className="flex items-center justify-center py-16 text-[11px]" style={{ color: T.muted }}>
                {parityReport ? "No fixture data from this run." : "Run a migration to see fixture diffs."}
              </div>
            ) : (
              <>
                {parityReport?.summary && (
                  <div className="px-4 py-3 text-[11px]" style={{ borderBottom: `1px solid ${T.border}`, color: overallColor }}>
                    {parityReport.summary}
                  </div>
                )}
                {fixtureCases.map((c, i) => <FixtureRow key={i} fixture={c} />)}
              </>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
