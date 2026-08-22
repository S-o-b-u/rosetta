"use client";

import React from "react";
import { useMigration } from "@/lib/migration";
import { IconBraces, IconCode } from "@tabler/icons-react";

export function AstApp() {
  const { state } = useMigration();
  const { neo4jContext, discoveryData, architectureData, validatorData } = state;

  return (
    <div className="flex h-full bg-[#1e1e1e] text-[#d4d4d4] overflow-hidden">
      {/* Sidebar: Pipeline Stages */}
      <div className="w-64 border-r border-white/10 flex flex-col bg-[#252526]">
        <div className="p-3 text-xs font-semibold uppercase tracking-wider text-zinc-500 border-b border-white/10">
          Pipeline State
        </div>
        <div className="flex-1 overflow-auto p-2 space-y-1 text-sm font-mono">
          <StageItem name="AST Ingestion" active={!!neo4jContext} />
          <StageItem name="Discovery" active={!!discoveryData} />
          <StageItem name="Architecture" active={!!architectureData} />
          <StageItem name="Validator" active={!!validatorData} />
        </div>
      </div>

      {/* Main Content: Raw JSON State */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="p-3 border-b border-white/10 flex items-center gap-2 bg-[#252526]">
          <IconCode size={16} className="text-blue-400" />
          <span className="text-sm font-semibold">State Inspector</span>
        </div>
        <div className="flex-1 overflow-auto p-4 font-mono text-xs">
          {neo4jContext ? (
            <div className="space-y-6">
              <Section title="AST / Neo4j Context" data={neo4jContext} />
              {discoveryData && <Section title="Discovery Data" data={discoveryData} />}
              {architectureData && <Section title="Architecture Data" data={architectureData} />}
              {validatorData && <Section title="Validator Data" data={validatorData} />}
            </div>
          ) : (
            <div className="text-zinc-500 flex items-center justify-center h-full">
              Waiting for AST ingestion...
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StageItem({ name, active }: { name: string; active: boolean }) {
  return (
    <div className={`px-2 py-1.5 rounded flex items-center gap-2 ${active ? 'text-zinc-200 bg-blue-500/10' : 'text-zinc-600'}`}>
      <IconBraces size={14} className={active ? "text-blue-400" : "text-zinc-700"} />
      {name}
    </div>
  );
}

function Section({ title, data }: { title: string; data: any }) {
  return (
    <div>
      <div className="text-zinc-400 mb-2 pb-1 border-b border-white/10 font-semibold">{title}</div>
      <pre className="text-emerald-400/90 whitespace-pre-wrap break-all">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}
