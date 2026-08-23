"use client";

import React from "react";
import { useMigration } from "@/lib/migration";

/* ── Subtle Monochrome + 2 Accent Palette ── */
const T = {
  bg:      "#000000",
  surface: "#0A0A0A",
  surface2:"#121212",
  border:  "#262626",
  text:    "#FFFFFF",
  dim:     "#A3A3A3",
  muted:   "#525252",
  accent:  "#E5E5E5",
  subtle:  "#1E1E1E",
  // Exactly 2 accent colors for AST highlights
  hi1:     "#3b82f6",   // blue - extracted dependencies
  hi2:     "#8b5cf6",   // purple - keywords & return
};

function PipelineStep({ label, done }: { label: string; done: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="w-2.5 h-2.5 rounded-full shrink-0"
        style={{ 
          background: done ? T.accent : T.surface2, 
          border: `1px solid ${done ? T.accent : T.border}`
        }}
      />
      <span className="text-[12px] font-medium tracking-wide" style={{ color: done ? T.text : T.dim }}>
        {label}
      </span>
      {done && (
        <span className="ml-auto text-[10px] font-bold" style={{ color: T.accent }}>✓</span>
      )}
    </div>
  );
}

function HighlightedJavaCode({ targetId, extractedNodes }: { targetId: string | null, extractedNodes: string[] }) {
  const isExtracted = (name: string) => extractedNodes.includes(name);

  return (
    <div className="font-mono text-[13px] leading-[1.8] w-full min-w-max">
      <div style={{ color: T.muted }}>{"/**"}</div>
      <div style={{ color: T.muted }}>{" * AST Parser resolving dependencies for "}{targetId ?? "target"}{"..."}</div>
      <div style={{ color: T.muted }}>{" */"}</div>
      <div className="mt-2 flex">
        <span style={{ color: T.hi2, width: "60px" }}>public</span>
        <span style={{ color: T.dim, width: "90px" }}>BigDecimal</span>
        <span style={{ color: T.text }} className="font-bold">getGrandTotal</span>
        <span style={{ color: T.dim }}>() {'{'}</span>
      </div>
      
      <div className="pl-8 border-l border-dashed mt-2" style={{ borderColor: T.border }}>
        <div>
          <span style={{ color: T.dim }}>BigDecimal</span> <span style={{ color: T.text }}>grandTotal = BigDecimal.ZERO;</span>
        </div>
        
        <div className="mt-4" style={{ color: T.muted }}>// Extracted AST Dependency</div>
        <div>
          <span style={{ color: T.dim }}>grandTotal = grandTotal.</span><span style={{ color: T.text }}>add</span>(
          <span 
            className="px-1.5 py-0.5 mx-0.5 rounded font-medium transition-colors" 
            style={{ 
              background: isExtracted("getSubTotal") ? T.hi1 + "20" : "transparent",
              color: isExtracted("getSubTotal") ? T.hi1 : T.dim 
            }}
          >
            getSubTotal()
          </span>);
        </div>
        
        <div className="mt-4" style={{ color: T.muted }}>// Extracted AST Dependency</div>
        <div>
          <span style={{ color: T.dim }}>grandTotal = grandTotal.</span><span style={{ color: T.text }}>add</span>(
          <span 
            className="px-1.5 py-0.5 mx-0.5 rounded font-medium transition-colors" 
            style={{ 
              background: isExtracted("getTotalShipping") ? T.hi1 + "20" : "transparent", 
              color: isExtracted("getTotalShipping") ? T.hi1 : T.dim 
            }}
          >
            getTotalShipping()
          </span>);
        </div>

        <div className="mt-4" style={{ color: T.muted }}>// Extracted AST Dependency</div>
        <div>
          <span style={{ color: T.dim }}>grandTotal = grandTotal.</span><span style={{ color: T.text }}>add</span>(
          <span 
            className="px-1.5 py-0.5 mx-0.5 rounded font-medium transition-colors" 
            style={{ 
              background: isExtracted("getTotalSalesTax") ? T.hi1 + "20" : "transparent", 
              color: isExtracted("getTotalSalesTax") ? T.hi1 : T.dim 
            }}
          >
            getTotalSalesTax()
          </span>);
        </div>

        <div className="mt-4" style={{ color: T.muted }}>// Extracted AST Dependency</div>
        <div>
          <span style={{ color: T.dim }}>grandTotal = grandTotal.</span><span style={{ color: T.text }}>add</span>(
          <span 
            className="px-1.5 py-0.5 mx-0.5 rounded font-medium transition-colors" 
            style={{ 
              background: isExtracted("getOrderOtherAdjustmentTotal") ? T.hi1 + "20" : "transparent", 
              color: isExtracted("getOrderOtherAdjustmentTotal") ? T.hi1 : T.dim 
            }}
          >
            getOrderOtherAdjustmentTotal()
          </span>);
        </div>

        <div className="mt-4" style={{ color: T.muted }}>// Extracted AST Dependency</div>
        <div>
          <span style={{ color: T.dim }}>grandTotal = grandTotal.</span><span style={{ color: T.text }}>add</span>(
          <span 
            className="px-1.5 py-0.5 mx-0.5 rounded font-medium transition-colors" 
            style={{ 
              background: isExtracted("getOrderGlobalAdjustments") ? T.hi1 + "20" : "transparent", 
              color: isExtracted("getOrderGlobalAdjustments") ? T.hi1 : T.dim 
            }}
          >
            getOrderGlobalAdjustments()
          </span>);
        </div>

        <div className="mt-4">
          <span style={{ color: T.hi2 }}>return</span> <span style={{ color: T.text }}>grandTotal;</span>
        </div>
      </div>
      <div className="mt-2" style={{ color: T.dim }}>{'}'}</div>
    </div>
  );
}

export function AstApp() {
  const { state } = useMigration();
  const { neo4jContext, discoveryData } = state;

  const nodes = neo4jContext?.nodes ?? [];
  const edges = neo4jContext?.edges ?? [];
  const targetId = edges.length > 0 ? edges[0].source : (nodes[0]?.id || "getGrandTotal");
  const extractedNodeIds = nodes.map((n: { id: string }) => n.id);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const disc = discoveryData as any;
  const formulaIr = disc?.formula_ir ?? null;

  return (
    <div className="flex h-full overflow-hidden" style={{ background: T.bg, color: T.text }}>
      
      {/* ── LEFT SIDEBAR ── */}
      <div className="w-[280px] shrink-0 flex flex-col" style={{ borderRight: `1px solid ${T.border}`, background: T.surface }}>
        
        {/* Pipeline Section */}
        <div className="p-5" style={{ borderBottom: `1px solid ${T.border}` }}>
          <div className="text-[10px] font-bold tracking-widest mb-4" style={{ color: T.dim }}>AST PIPELINE</div>
          <div className="space-y-4">
            <PipelineStep label="Source Parsed" done={!!neo4jContext} />
            <PipelineStep label="Graph Ingested" done={!!neo4jContext} />
            <PipelineStep label="Logic Extracted" done={!!discoveryData} />
            <PipelineStep label="Formula Derived" done={!!discoveryData} />
          </div>
        </div>

        {/* Resolved Nodes Section */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="px-5 py-4 shrink-0 flex items-center justify-between" style={{ borderBottom: `1px solid ${T.border}` }}>
            <span className="text-[10px] font-bold tracking-widest" style={{ color: T.dim }}>RESOLVED NODES</span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded" style={{ background: T.surface2, color: T.text }}>
              {nodes.length}
            </span>
          </div>
          
          <div className="flex-1 overflow-auto p-3 space-y-1">
            {nodes.length > 0 ? (
              nodes.map((n: { id: string }) => (
                <div 
                  key={n.id} 
                  className="flex items-center gap-3 px-3 py-2 rounded-md cursor-default hover:bg-white/5 transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={n.id === targetId ? T.accent : T.dim} strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 8v8M8 12h8" />
                  </svg>
                  <span className="text-[12px] font-mono truncate" style={{ color: n.id === targetId ? T.text : T.dim }}>
                    {n.id}()
                  </span>
                </div>
              ))
            ) : (
              <div className="px-3 py-4 text-[12px] italic text-center" style={{ color: T.muted }}>
                Awaiting AST parse...
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── RIGHT MAIN AREA ── */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Editor Header */}
        <div className="h-[48px] shrink-0 flex items-center px-5 gap-3" style={{ borderBottom: `1px solid ${T.border}`, background: T.surface2 }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.dim} strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          <span className="text-[13px] font-medium" style={{ color: T.text }}>ShoppingCart.java</span>
          <span className="ml-auto text-[11px] font-mono px-2 py-1 rounded" style={{ background: T.bg, color: T.dim, border: `1px solid ${T.border}` }}>
            {targetId}()
          </span>
        </div>

        {/* Source Code Container */}
        <div className="flex-1 overflow-auto p-6 bg-[#000000]">
          <HighlightedJavaCode targetId={targetId} extractedNodes={extractedNodeIds} />
        </div>

        {/* Bottom Formula IR Pane (Only visible when derived) */}
        {formulaIr && (
          <div className="shrink-0 p-5 shadow-2xl" style={{ borderTop: `1px solid ${T.border}`, background: T.surface }}>
            <div className="flex items-center gap-2 mb-3">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={T.accent} strokeWidth="2">
                <path d="M4 7V4h16v3M9 20h6M12 4v16" />
              </svg>
              <span className="text-[11px] font-bold tracking-widest" style={{ color: T.accent }}>
                EXTRACTED FORMULA (IR)
              </span>
            </div>
            
            <div className="font-mono text-[13px] bg-[#000000] border rounded-lg p-4" style={{ borderColor: T.border }}>
              <div className="flex items-center gap-3">
                <span style={{ color: T.dim }}>Target:</span>
                <span style={{ color: T.text }} className="font-semibold">{formulaIr.method_name}</span>
              </div>
              <div className="flex items-center gap-3 mt-2">
                <span style={{ color: T.dim }}>Logic:</span>
                <span style={{ color: T.text }} className="font-semibold">{formulaIr.formula}</span>
              </div>
              
              <div className="mt-4 pt-3 flex gap-6 overflow-x-auto" style={{ borderTop: `1px dashed ${T.border}` }}>
                {(formulaIr.formula_terms ?? []).map((t: { name: string; source_method: string }, i: number) => (
                  <div key={i} className="flex items-center gap-2 shrink-0 bg-white/5 px-2 py-1 rounded">
                    <span style={{ color: T.text }}>{t.name}</span>
                    <span style={{ color: T.muted }}>→</span>
                    <span style={{ color: T.dim }}>{t.source_method}()</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
