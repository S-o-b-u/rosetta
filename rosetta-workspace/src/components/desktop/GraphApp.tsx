"use client";

import React, { useMemo } from "react";
import { useMigration } from "@/lib/migration";

export function GraphApp() {
  const { state } = useMigration();
  const { neo4jContext } = state;

  const { nodes, edges } = useMemo(() => {
    if (!neo4jContext) return { nodes: [], edges: [] };
    return {
      nodes: neo4jContext.nodes || [],
      edges: neo4jContext.edges || [],
    };
  }, [neo4jContext]);

  if (!neo4jContext) {
    return (
      <div className="flex items-center justify-center h-full bg-[#1e1e1e] text-zinc-500 font-mono text-sm">
        Waiting for graph data...
      </div>
    );
  }

  // Simple layout: target method on top, called methods below
  const targetNodeId = edges.length > 0 ? edges[0].source : nodes[0]?.id;
  
  const targetNode = nodes.find(n => n.id === targetNodeId);
  const childNodes = nodes.filter(n => n.id !== targetNodeId);

  return (
    <div className="flex flex-col h-full bg-[#1e1e1e] text-[#d4d4d4] font-mono p-6 relative overflow-hidden">
      <div className="text-xs text-zinc-500 mb-8 absolute top-4 left-4 z-10">
        Neo4j Knowledge Graph (CALLS Relationships)
      </div>

      <div className="flex-1 w-full h-full flex flex-col items-center justify-center relative">
        {/* Draw SVG lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
          {childNodes.map((child, i) => {
            // Target is top-center
            const x1 = "50%";
            const y1 = "25%";
            
            // Children spread evenly along bottom
            const spread = 80; // percentage
            const step = childNodes.length > 1 ? spread / (childNodes.length - 1) : 0;
            const startX = childNodes.length > 1 ? (100 - spread) / 2 : 50;
            const x2 = `${startX + (i * step)}%`;
            const y2 = "75%";

            return (
              <g key={`edge-${i}`}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke="#3b82f6"
                  strokeWidth="2"
                  strokeOpacity="0.4"
                />
                <circle cx={x2} cy={y2} r="4" fill="#3b82f6" opacity="0.6" />
              </g>
            );
          })}
        </svg>

        {/* Draw DOM Nodes */}
        <div className="absolute inset-0 w-full h-full pointer-events-none">
          {targetNode && (
            <div 
              className="absolute left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto"
              style={{ top: "25%" }}
            >
              <NodeCard id={targetNode.id} label={targetNode.label} isTarget />
            </div>
          )}

          {childNodes.map((child, i) => {
            const spread = 80;
            const step = childNodes.length > 1 ? spread / (childNodes.length - 1) : 0;
            const startX = childNodes.length > 1 ? (100 - spread) / 2 : 50;
            const left = `${startX + (i * step)}%`;

            return (
              <div 
                key={child.id}
                className="absolute -translate-x-1/2 -translate-y-1/2 pointer-events-auto"
                style={{ top: "75%", left }}
              >
                <NodeCard id={child.id} label={child.label} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function NodeCard({ id, label, isTarget = false }: { id: string; label: string; isTarget?: boolean }) {
  return (
    <div className={`
      px-4 py-2 rounded-lg border backdrop-blur-md whitespace-nowrap shadow-xl transition-transform hover:scale-105 cursor-pointer
      ${isTarget 
        ? "bg-blue-900/40 border-blue-500/50 text-blue-100" 
        : "bg-zinc-800/80 border-zinc-600/50 text-zinc-300"
      }
    `}>
      <div className="text-[10px] uppercase tracking-wider opacity-60 mb-0.5">{label}</div>
      <div className="text-sm font-semibold">{id}</div>
    </div>
  );
}
