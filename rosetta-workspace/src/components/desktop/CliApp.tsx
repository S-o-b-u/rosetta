"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { useMigration, type MigrationEvent } from "@/lib/migration";

/* ── Palette ── */
const C = {
  bg: "#0d1117",
  panel: "#161b22",
  border: "#30363d",
  prompt: "#7ee787",
  cmd: "#e6edf3",
  dim: "#484f58",
  blue: "#58a6ff",
  cyan: "#56d4dd",
  yellow: "#d29922",
  orange: "#f0883e",
  red: "#f85149",
  green: "#3fb950",
  purple: "#bc8cff",
  white: "#f0f6fc",
};

/* ── Pretty-print a single pipeline event for the terminal ── */
function formatEvent(evt: MigrationEvent): { prefix: string; color: string; lines: string[] } {
  const ts = new Date(evt.timestamp).toLocaleTimeString("en-US", { hour12: false });

  if (evt.event === "migration_started") {
    const d = evt.data as Record<string, string>;
    return {
      prefix: ts,
      color: C.green,
      lines: [
        `⚡  Migration started`,
        `   migration_id : ${d.migration_id}`,
        `   file         : ${d.file_path}`,
        `   method       : ${d.target_method}`,
      ],
    };
  }

  if (evt.event === "node" && evt.node === "ast_context_node") {
    const ctx = (evt.data as any)?.state?.neo4j_context;
    const nNodes = ctx?.nodes?.length ?? 0;
    const nEdges = ctx?.edges?.length ?? 0;
    const nodeIds = (ctx?.nodes ?? []).map((n: { id: string }) => n.id).join(", ");
    return {
      prefix: ts,
      color: C.cyan,
      lines: [
        `◆  AST Context Node`,
        `   ${nNodes} nodes, ${nEdges} edges`,
        `   services: ${nodeIds}`,
      ],
    };
  }

  if (evt.event === "node" && evt.node === "discovery_agent") {
    const s = (evt.data as any)?.state ?? {};
    const formula = s.formula_ir?.formula ?? "—";
    const nTests = s.test_cases?.length ?? 0;
    return {
      prefix: ts,
      color: C.blue,
      lines: [
        `◆  Discovery Agent`,
        `   formula : ${formula}`,
        `   tests   : ${nTests} case(s) generated`,
      ],
    };
  }

  if (evt.event === "node" && evt.node === "architecture_agent") {
    const s = (evt.data as any)?.state ?? {};
    const retry = s.retry_count ?? "?";
    const srcLen = (s.generated_python ?? "").length;
    return {
      prefix: ts,
      color: C.purple,
      lines: [
        `◆  Architecture Agent  (attempt ${retry})`,
        `   generated ${srcLen} chars of Python`,
      ],
    };
  }

  if (evt.event === "node" && evt.node === "validator") {
    const s = (evt.data as any)?.state ?? {};
    const passed = s.validation_passed;
    const pr = s.parity_report;
    const summary = pr?.summary ?? s.validation_feedback ?? "—";
    return {
      prefix: ts,
      color: passed ? C.green : C.red,
      lines: [
        `◆  Validator  ${passed ? "✔ PASS" : "✘ FAIL"}`,
        `   ${summary}`,
      ],
    };
  }

  if (evt.event === "migration_completed") {
    return {
      prefix: ts,
      color: C.green,
      lines: [`✔  Migration completed successfully`],
    };
  }

  if (evt.event === "error") {
    return {
      prefix: ts,
      color: C.red,
      lines: [`✘  Error: ${(evt.data as any)?.error ?? "unknown"}`],
    };
  }

  if (evt.event === "stream_end") {
    return {
      prefix: ts,
      color: C.dim,
      lines: [`─── stream ended ───`],
    };
  }

  // fallback
  return {
    prefix: ts,
    color: C.dim,
    lines: [`[${evt.event}] ${JSON.stringify(evt.data).slice(0, 120)}`],
  };
}

export function CliApp() {
  const { state, startMigration } = useMigration();
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const HOST = "rosetta";
  const DIR = "~/sandbox";

  // Auto-scroll on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [state.events, history]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const cmd = input.trim();
      if (!cmd) return;
      setInput("");

      // Parse command
      const parts = cmd.split(/\s+/);
      const base = parts[0];

      if (base === "clear") {
        setHistory([]);
        return;
      }

      if (base === "help") {
        setHistory((h) => [
          ...h,
          `$ ${cmd}`,
          "",
          "  rosetta migrate <file> <method>   Run the migration pipeline",
          "  clear                             Clear terminal",
          "  help                              Show this help",
          "",
        ]);
        return;
      }

      if (base === "rosetta" && parts[1] === "migrate") {
        const file =
          parts[2] ||
          "ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java";
        const method = parts[3] || "getGrandTotal";
        setHistory((h) => [
          ...h,
          `$ ${cmd}`,
          `  → file   : ${file}`,
          `  → method : ${method}`,
          "",
        ]);
        startMigration(file, method);
        return;
      }

      setHistory((h) => [
        ...h,
        `$ ${cmd}`,
        `  command not found: ${base}. Type 'help' for usage.`,
        "",
      ]);
    },
    [input, startMigration]
  );

  const focusInput = () => inputRef.current?.focus();

  return (
    <div
      className="flex flex-col h-full font-mono text-[13px] leading-[1.6] select-text cursor-text"
      style={{ background: C.bg, color: C.cmd }}
      onClick={focusInput}
    >
      {/* ── Scrollable output ── */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-4 pt-3 pb-1">
        {/* ASCII art banner */}
        <div className="mb-3 leading-[1.1] text-[10px]" style={{ fontFamily: "monospace" }}>
          {[
            "██████╗  ██████╗ ███████╗███████╗████████╗████████╗ █████╗ ",
            "██╔══██╗██╔═══██╗██╔════╝██╔════╝╚══██╔══╝╚══██╔══╝██╔══██╗",
            "██████╔╝██║   ██║███████╗█████╗     ██║      ██║   ███████║",
            "██╔══██╗██║   ██║╚════██║██╔══╝     ██║      ██║   ██╔══██║",
            "██║  ██║╚██████╔╝███████║███████╗   ██║      ██║   ██║  ██║",
            "╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚══════╝   ╚═╝      ╚═╝   ╚═╝  ╚═╝",
          ].map((line, i) => {
            const colors = ["#8be9fd", "#78dce8", "#66d0d4", "#54c4c0", "#42b8ac", "#30ac98"];
            return (
              <div
                key={i}
                className="whitespace-pre"
                style={{
                  color: colors[i],
                  textShadow: `0 0 10px ${colors[i]}40`,
                }}
              >
                {line}
              </div>
            );
          })}
          <div className="mt-2" style={{ color: C.dim }}>
            Migration Engine v1.0 — type{" "}
            <span style={{ color: C.prompt }}>help</span> for commands
          </div>
        </div>

        {/* Command history */}
        {history.map((line, i) => (
          <div key={`h-${i}`} className="whitespace-pre-wrap">
            {line.startsWith("$") ? (
              <>
                <span style={{ color: C.prompt }}>{HOST}</span>
                <span style={{ color: C.dim }}>:</span>
                <span style={{ color: C.blue }}>{DIR}</span>
                <span style={{ color: C.cmd }}> {line}</span>
              </>
            ) : (
              <span style={{ color: C.dim }}>{line}</span>
            )}
          </div>
        ))}

        {/* Pipeline events */}
        {state.events.map((evt) => {
          const { prefix, color, lines } = formatEvent(evt);
          return (
            <div key={evt.id} className="mb-1">
              {lines.map((line, li) => (
                <div key={li} className="whitespace-pre-wrap">
                  {li === 0 ? (
                    <>
                      <span style={{ color: C.dim }}>{prefix}  </span>
                      <span style={{ color }}>{line}</span>
                    </>
                  ) : (
                    <span style={{ color: C.dim }}>{`            ${line}`}</span>
                  )}
                </div>
              ))}
            </div>
          );
        })}

        {/* Active spinner */}
        {state.status === "running" && (
          <div className="flex items-center gap-2 mt-1">
            <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: C.green }} />
            <span style={{ color: C.dim }}>
              pipeline running — {state.currentNode ?? "..."}
            </span>
          </div>
        )}
      </div>

      {/* ── Input prompt ── */}
      <div className="shrink-0 px-4 py-2 flex items-center gap-0" style={{ borderTop: `1px solid ${C.border}` }}>
        <span style={{ color: C.prompt }}>{HOST}</span>
        <span style={{ color: C.dim }}>:</span>
        <span style={{ color: C.blue }}>{DIR}</span>
        <span style={{ color: C.cmd }} className="mx-1">
          $
        </span>
        <form onSubmit={handleSubmit} className="flex-1">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="w-full bg-transparent outline-none caret-white"
            style={{ color: C.cmd }}
            autoFocus
            spellCheck={false}
            placeholder={state.status === "idle" ? "rosetta migrate <file> <method>" : ""}
          />
        </form>
      </div>
    </div>
  );
}
