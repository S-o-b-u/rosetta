"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useMigration, type MigrationEvent } from "@/lib/migration";

/* ── Vibrant, Smooth Modern Terminal Palette ── */
const C = {
  bg: "transparent",
  text: "#FFFFFF",
  dim: "#999999",
  blue: "#3291FF",
  cyan: "#00E5FF",
  yellow: "#F5A623",
  red: "#FF3366",
  green: "#00E676",
  purple: "#C879FF",
};

/* ── Format event cleanly ── */
function formatEvent(evt: MigrationEvent): { color: string; title: string; lines: string[] } {
  if (evt.event === "migration_started") {
    const d = evt.data as Record<string, string>;
    return {
      color: C.green,
      title: "MIGRATION_INIT",
      lines: [
        `ID:     ${d.migration_id}`,
        `File:   ${d.file_path}`,
        `Method: ${d.target_method}`
      ],
    };
  }
  if (evt.event === "node" && evt.node === "ast_context_node") {
    const ctx = (evt.data as any)?.state?.neo4j_context;
    return {
      color: C.cyan,
      title: "AST_DISCOVERY",
      lines: [
        `Status: Parsed source into graph space`,
        `Nodes:  ${ctx?.nodes?.length ?? 0} extracted`,
        `Edges:  ${ctx?.edges?.length ?? 0} mapped dependencies`
      ],
    };
  }
  if (evt.event === "node" && evt.node === "discovery_agent") {
    const s = (evt.data as any)?.state ?? {};
    return {
      color: C.blue,
      title: "LOGIC_EXTRACTION",
      lines: [
        `IR Formula: ${s.formula_ir?.formula ?? "none"}`,
        `Test Cases: ${s.test_cases?.length ?? 0} golden constraints generated`
      ],
    };
  }
  if (evt.event === "node" && evt.node === "architecture_agent") {
    const s = (evt.data as any)?.state ?? {};
    return {
      color: C.purple,
      title: "ARCHITECTURE_SYNTHESIS",
      lines: [
        `Attempt: ${s.retry_count ?? "?"}`,
        `Output:  Synthesized ${(s.generated_python ?? "").length} bytes of Python`
      ],
    };
  }
  if (evt.event === "node" && evt.node === "validator") {
    const s = (evt.data as any)?.state ?? {};
    const passed = s.validation_passed;
    return {
      color: passed ? C.green : C.red,
      title: "SHADOW_VALIDATOR",
      lines: [
        `Result:  ${passed ? "PASS" : "FAIL"}`,
        `Summary: ${s.parity_report?.summary ?? s.validation_feedback ?? ""}`
      ],
    };
  }
  if (evt.event === "migration_completed") {
    return {
      color: C.green,
      title: "SUCCESS",
      lines: [`Workflow completed without errors.`],
    };
  }
  if (evt.event === "error") {
    return {
      color: C.red,
      title: "FATAL_ERROR",
      lines: [`${(evt.data as any)?.error ?? "Unknown execution error"}`],
    };
  }
  if (evt.event === "stream_end") {
    return {
      color: C.dim,
      title: "SYS",
      lines: [`Stream closed.`],
    };
  }
  return {
    color: C.dim,
    title: "RAW",
    lines: [`${JSON.stringify(evt.data).slice(0, 80)}`],
  };
}

export function CliApp() {
  const { state, startMigration } = useMigration();
  const [input, setInput] = useState("");
  
  // History now just holds raw elements to render sequentially
  const [history, setHistory] = useState<React.ReactNode[]>([]);
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.events, history, input]);

  // Handle clicking anywhere to focus input
  const handleWrapperClick = () => {
    const selection = window.getSelection();
    if (!selection || selection.toString().length === 0) {
      inputRef.current?.focus();
    }
  };

  const Prompt = () => (
    <div className="flex items-center gap-2 shrink-0 select-none mr-2">
      <span style={{ color: C.green }} className="font-semibold">recast</span>
      <span style={{ color: C.dim }}>in</span>
      <span style={{ color: C.blue }} className="font-semibold">~/sandbox</span>
      <span style={{ color: C.dim }}>❯</span>
    </div>
  );

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const cmd = input.trim();
      if (!cmd) {
        setHistory(h => [...h, <div key={h.length} className="flex mt-1"><Prompt /></div>]);
        return;
      }
      setInput("");

      const currentCmdNode = (
        <div key={history.length} className="flex mt-2 mb-1">
          <Prompt />
          <span style={{ color: C.text }} className="font-medium">{cmd}</span>
        </div>
      );

      const parts = cmd.split(/\s+/);
      const base = parts[0];

      if (base === "clear") {
        setHistory([]);
        return;
      }

      let responseNode: React.ReactNode = null;

      if (base === "help") {
        responseNode = (
          <div key={history.length + "_res"} className="py-2 pl-4" style={{ color: C.text }}>
            <div className="font-semibold mb-2" style={{ color: C.cyan }}>Recast CLI (v1.0.0)</div>
            <div className="grid grid-cols-[100px_1fr] gap-2">
              <span style={{ color: C.blue }}>migrate</span><span style={{ color: C.dim }}>Start the migration pipeline</span>
              <span style={{ color: C.blue }}>clear</span><span style={{ color: C.dim }}>Clear the terminal output</span>
              <span style={{ color: C.blue }}>help</span><span style={{ color: C.dim }}>Show this help message</span>
            </div>
          </div>
        );
      } else if ((base === "recast" || base === "rosetta") && parts[1] === "migrate") {
        const file = parts[2] || "ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java";
        const method = parts[3] || "getGrandTotal";
        startMigration(file, method);
      } else {
        responseNode = (
          <div key={history.length + "_res"} className="py-1" style={{ color: C.red }}>
            zsh: command not found: {base}
          </div>
        );
      }

      setHistory(h => {
        const next = [...h, currentCmdNode];
        if (responseNode) next.push(responseNode);
        return next;
      });
    },
    [input, startMigration, history]
  );

  return (
    <div
      className="flex flex-col h-full w-full select-text cursor-text overflow-hidden"
      style={{ 
        background: "rgba(10, 10, 10, 0.7)", 
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        color: C.text,
        fontFamily: '"SF Mono", SFMono-Regular, ui-monospace, Menlo, Monaco, Consolas, monospace',
        fontSize: "13px",
        lineHeight: "1.6",
      }}
      onClick={handleWrapperClick}
    >
      <div ref={scrollRef} className="flex-1 overflow-auto px-5 py-4">
        
        {/* Banner - ALWAYS VISIBLE AT TOP */}
        <div className="mb-6">
          <div className="text-[10px] leading-tight select-none tracking-tight">
            {[
              "██████╗ ███████╗ ██████╗ █████╗ ███████╗████████╗",
              "██╔══██╗██╔════╝██╔════╝██╔══██╗██╔════╝╚══██╔══╝",
              "██████╔╝█████╗  ██║     ███████║███████╗   ██║   ",
              "██╔══██╗██╔══╝  ██║     ██╔══██║╚════██║   ██║   ",
              "██║  ██║███████╗╚██████╗██║  ██║███████║   ██║   ",
              "╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ",
            ].map((line, i) => {
              const colors = ["#00E5FF", "#18D5FF", "#30C5FF", "#48B5FF", "#60A5FF", "#7895FF"];
              return (
                <div key={i} className="whitespace-pre font-bold" style={{ color: colors[i] }}>
                  {line}
                </div>
              );
            })}
          </div>
          <div className="mt-4" style={{ color: C.dim }}>
            Welcome to Recast. Type <span style={{ color: C.cyan }} className="font-semibold">help</span> to view commands.
          </div>
        </div>

        {/* History stream */}
        <div className="flex flex-col">
          {history}
        </div>

        {/* Live Pipeline Events */}
        {state.events.length > 0 && (
          <div className="mt-4 flex flex-col gap-3">
            {state.events.map((evt) => {
              const { color, title, lines } = formatEvent(evt);
              const ts = new Date(evt.timestamp).toLocaleTimeString("en-US", { hour12: false });
              return (
                <div key={evt.id} className="flex gap-4">
                  <div className="w-[70px] shrink-0 text-right pt-0.5" style={{ color: C.dim, fontSize: "11px" }}>
                    {ts}
                  </div>
                  <div className="flex-1">
                    <div className="font-bold flex items-center gap-2 mb-1" style={{ color }}>
                      <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
                      {title}
                    </div>
                    <div className="pl-3 border-l-2" style={{ borderColor: color + "40" }}>
                      {lines.map((line, li) => (
                        <div key={li} className="whitespace-pre-wrap font-medium" style={{ color: C.text }}>
                          {line}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Active Inline Prompt Line */}
        <div className="flex items-center mt-4 mb-2">
          {state.status === "running" ? (
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin" style={{ borderColor: C.blue, borderTopColor: "transparent" }} />
              <span style={{ color: C.blue }} className="font-medium">Waiting for {state.currentNode ?? "..."}</span>
            </div>
          ) : (
            <div className="flex items-center w-full">
              <Prompt />
              <form onSubmit={handleSubmit} className="flex-1">
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  className="w-full bg-transparent outline-none border-none p-0 m-0 font-medium"
                  style={{ color: C.text }}
                  autoFocus
                  spellCheck={false}
                  autoComplete="off"
                />
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
