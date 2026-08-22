"use client";

import React, { useState } from "react";
import { useMigration } from "@/lib/migration";

export function CliApp() {
  const { state, startMigration } = useMigration();
  const [filePath, setFilePath] = useState(
    "ofbiz-framework/applications/order/src/main/java/org/apache/ofbiz/order/shoppingcart/ShoppingCart.java"
  );
  const [targetMethod, setTargetMethod] = useState("getGrandTotal");

  const handleStart = (e: React.FormEvent) => {
    e.preventDefault();
    startMigration(filePath, targetMethod);
  };

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e] text-[#d4d4d4] font-mono text-sm">
      <div className="p-4 border-b border-white/10 shrink-0 bg-[#252526]">
        <form onSubmit={handleStart} className="flex gap-2 items-end">
          <div className="flex-1 space-y-1">
            <label className="block text-xs text-zinc-400">Target File</label>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              className="w-full bg-[#3c3c3c] border border-transparent focus:border-blue-500 rounded px-2 py-1 outline-none text-white text-xs"
            />
          </div>
          <div className="w-48 space-y-1">
            <label className="block text-xs text-zinc-400">Method</label>
            <input
              type="text"
              value={targetMethod}
              onChange={(e) => setTargetMethod(e.target.value)}
              className="w-full bg-[#3c3c3c] border border-transparent focus:border-blue-500 rounded px-2 py-1 outline-none text-white text-xs"
            />
          </div>
          <button
            type="submit"
            disabled={state.status === "running"}
            className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-1 rounded text-xs transition-colors h-[26px]"
          >
            {state.status === "running" ? "Running..." : "Run Pipeline"}
          </button>
        </form>
      </div>
      
      <div className="flex-1 overflow-auto p-4 space-y-1 bg-[#1e1e1e]">
        <div className="text-emerald-400 mb-4">$ rosetta migrate --live-stream</div>
        {state.events.map((evt) => (
          <div key={evt.id} className="flex gap-4 hover:bg-white/5 py-0.5 px-1 rounded">
            <span className="text-zinc-500 shrink-0 w-24">
              {new Date(evt.timestamp).toLocaleTimeString()}
            </span>
            <span className="text-blue-400 w-32 shrink-0">
              [{evt.event === "node" ? evt.node : evt.event}]
            </span>
            <span className="text-zinc-300 break-all whitespace-pre-wrap">
              {JSON.stringify(evt.data)}
            </span>
          </div>
        ))}
        {state.status === "running" && (
          <div className="animate-pulse text-zinc-500">_</div>
        )}
        {state.error && (
          <div className="text-red-400 mt-2">Error: {state.error}</div>
        )}
      </div>
    </div>
  );
}
