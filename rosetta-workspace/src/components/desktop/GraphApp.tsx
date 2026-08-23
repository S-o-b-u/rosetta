"use client";

import React, { useRef, useEffect, useMemo, useCallback, useState } from "react";
import { useMigration, type GraphNode, type GraphEdge } from "@/lib/migration";
import dynamic from "next/dynamic";

const ForceGraph3D = dynamic(() => import("react-force-graph-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-zinc-600 text-sm font-mono">
      <div className="flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-blue-500/40 border-t-blue-400 rounded-full animate-spin" />
        <span>Loading 3D engine…</span>
      </div>
    </div>
  ),
});

/* ── Palette ── */
const P = {
  bg: "#0d1117", 
  panel: "#161b22",
  border: "#30363d",
  nodePrimary: "#58a6ff", 
  nodeSecondary: "#56d4dd",
  edgeLine: "#1e3a5f",
  labelText: "#f0f6fc",
  dim: "#8b949e",
  purple: "#bc8cff",
};

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-2 h-2 rounded-full" style={{ background: color }} />
      <span className="text-[10px] font-mono" style={{ color: "#6b7280" }}>{label}</span>
    </div>
  );
}

export function GraphApp() {
  const { state } = useMigration();
  const { neo4jContext } = state;
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<any>(null);
  const [dims, setDims] = useState({ w: 800, h: 500 });
  const [hovered, setHovered] = useState<string | null>(null);

  // ── Resize observer ──
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      for (const e of entries) {
        const { width, height } = e.contentRect;
        if (width > 0 && height > 0)
          setDims({ w: Math.floor(width), h: Math.floor(height) });
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // ── Graph data from real neo4j_context ──
  const graphData = useMemo(() => {
    if (!neo4jContext?.nodes?.length) return { nodes: [], links: [] };
    const targetId = neo4jContext.edges?.length > 0
      ? neo4jContext.edges[0].source
      : neo4jContext.nodes[0]?.id;
    return {
      nodes: neo4jContext.nodes.map((n: GraphNode) => ({
        id: n.id,
        label: n.id,
        isTarget: n.id === targetId,
        val: n.id === targetId ? 12 : 6,
      })),
      links: (neo4jContext.edges ?? []).map((e: GraphEdge) => ({
        source: e.source,
        target: e.target,
        label: e.label,
      })),
    };
  }, [neo4jContext]);

  // ── Custom 3D node rendering ──
  const nodeThreeObject = useCallback(
    (node: any) => {
      const THREE = require("three");
      const isTarget = node.isTarget;
      const isHov = hovered === node.id;
      const group = new THREE.Group();

      const radius = isTarget ? 6 : 4;
      const color = isTarget ? P.nodePrimary : P.nodeSecondary;

      // Core sphere
      const geo = new THREE.SphereGeometry(radius, 32, 32);
      const mat = new THREE.MeshPhongMaterial({
        color: new THREE.Color(color),
        emissive: new THREE.Color(color),
        emissiveIntensity: isHov ? 0.5 : 0.15,
        shininess: 80,
        transparent: true,
        opacity: 0.95,
      });
      group.add(new THREE.Mesh(geo, mat));

      // Glow halo (only for hover or target)
      if (isTarget || isHov) {
        const glowGeo = new THREE.SphereGeometry(radius * 1.8, 16, 16);
        const glowMat = new THREE.MeshBasicMaterial({
          color: new THREE.Color(color),
          transparent: true,
          opacity: isHov ? 0.1 : 0.05,
          side: THREE.BackSide,
        });
        group.add(new THREE.Mesh(glowGeo, glowMat));
      }

      // Text label sprite
      const scale = 2;
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d")!;
      const fontSize = (isTarget ? 24 : 18) * scale;
      const text = node.id;
      ctx.font = `600 ${fontSize}px "Inter", system-ui, sans-serif`;
      const tm = ctx.measureText(text);
      const pad = 14 * scale;
      const cw = tm.width + pad * 2;
      const ch = fontSize + pad * 1.2;
      canvas.width = cw;
      canvas.height = ch;

      // Pill background
      ctx.fillStyle = "rgba(7, 11, 20, 0.85)";
      const rr = ch / 2;
      ctx.beginPath();
      ctx.roundRect(0, 0, cw, ch, rr);
      ctx.fill();

      // Border
      ctx.strokeStyle = `${color}50`;
      ctx.lineWidth = 1.5 * scale;
      ctx.beginPath();
      ctx.roundRect(0, 0, cw, ch, rr);
      ctx.stroke();

      // Text
      ctx.font = `600 ${fontSize}px "Inter", system-ui, sans-serif`;
      ctx.fillStyle = isTarget ? P.nodePrimary : P.labelText;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, cw / 2, ch / 2);

      const tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      const spriteMat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false });
      const sprite = new THREE.Sprite(spriteMat);
      const ss = 0.04;
      sprite.scale.set(cw * ss, ch * ss, 1);
      sprite.position.set(0, radius + 3.5, 0);
      group.add(sprite);

      return group;
    },
    [hovered]
  );

  // ── Scene setup ──
  const handleEngineStop = useCallback(() => {
    if (!fgRef.current) return;
    const THREE = require("three");
    const scene = fgRef.current.scene?.();
    if (!scene) return;

    // Only add lights once
    if (scene.userData.__lightsAdded) return;
    scene.userData.__lightsAdded = true;

    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambient);

    const dir = new THREE.DirectionalLight(0x58a6ff, 0.8);
    dir.position.set(60, 80, 60);
    scene.add(dir);

    const fill = new THREE.DirectionalLight(0x56d4dd, 0.3);
    fill.position.set(-40, -20, -50);
    scene.add(fill);
  }, []);

  // ── Fit + setup on data change ──
  useEffect(() => {
    if (fgRef.current && graphData.nodes.length > 0) {
      const t = setTimeout(() => {
        // Zoom tighter on first glance
        fgRef.current?.zoomToFit?.(600, 20);
        const dist = fgRef.current.cameraPosition().z;
        if (dist > 150) {
          fgRef.current.cameraPosition({ z: 120 }, null, 600);
        }
      }, 500);
      return () => clearTimeout(t);
    }
  }, [graphData]);

  // ── Empty state ──
  if (!neo4jContext || graphData.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full font-mono gap-4" style={{ background: P.bg }}>
        <div className="w-16 h-16 rounded border flex items-center justify-center" style={{ borderColor: P.border, background: P.panel }}>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke={P.dim} strokeWidth="1.5">
            <circle cx="12" cy="5" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="19" cy="19" r="2" />
            <line x1="12" y1="7" x2="5" y2="17" />
            <line x1="12" y1="7" x2="19" y2="17" />
          </svg>
        </div>
        <div className="text-[12px] font-medium" style={{ color: P.labelText }}>Knowledge Graph</div>
        <div className="text-[11px]" style={{ color: P.dim }}>Run a migration to visualize dependencies</div>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="relative w-full h-full overflow-hidden" style={{ background: P.bg }}>
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={dims.w}
        height={dims.h}
        backgroundColor={P.bg}
        showNavInfo={false}
        enableNavigationControls={true}
        // Nodes
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        nodeLabel={() => ""}
        // Links
        linkColor={() => P.edgeLine}
        linkWidth={1.5}
        linkOpacity={0.6}
        linkDirectionalArrowLength={5}
        linkDirectionalArrowRelPos={0.85}
        linkDirectionalArrowColor={() => P.nodeSecondary + "99"}
        linkDirectionalParticles={2}
        linkDirectionalParticleWidth={1.5}
        linkDirectionalParticleColor={() => P.nodePrimary}
        linkDirectionalParticleSpeed={0.006}
        // Interaction
        onNodeHover={(n: any) => setHovered(n?.id ?? null)}
        // Engine
        onEngineStop={handleEngineStop}
        d3AlphaDecay={0.025}
        d3VelocityDecay={0.3}
        warmupTicks={80}
        cooldownTicks={0}
      />

      {/* HUD top-left */}
      <div className="absolute top-0 left-0 right-0 p-3 flex justify-between pointer-events-none">
        <div>
          <div className="text-[11px] font-semibold font-mono" style={{ color: P.labelText }}>
            Knowledge Graph
          </div>
          <div className="text-[10px] font-mono mt-0.5" style={{ color: P.dim }}>
            {graphData.nodes.length} nodes · {graphData.links.length} edges
          </div>
        </div>
        <div className="text-[9px] font-mono text-right" style={{ color: P.dim }}>
          left drag: rotate · scroll: zoom · right drag: pan
        </div>
      </div>

      {/* Legend */}
      <div
        className="absolute bottom-3 left-3 flex flex-col gap-1.5 px-3 py-2 pointer-events-none"
        style={{ background: P.panel, border: `1px solid ${P.border}` }}
      >
        <LegendDot color={P.nodePrimary} label="Target method" />
        <LegendDot color={P.nodeSecondary} label="Dependency" />
      </div>

      {/* Hover info */}
      {hovered && (
        <div
          className="absolute bottom-3 right-3 px-3 py-2 font-mono text-[11px] pointer-events-none text-right"
          style={{ background: P.panel, border: `1px solid ${P.border}` }}
        >
          <div style={{ color: P.nodePrimary }} className="font-semibold">{hovered}</div>
          <div className="text-[10px] mt-0.5" style={{ color: P.dim }}>
            {graphData.links.filter((l: any) =>
              (typeof l.source === "string" ? l.source : l.source?.id) === hovered
            ).length} out ·{" "}
            {graphData.links.filter((l: any) =>
              (typeof l.target === "string" ? l.target : l.target?.id) === hovered
            ).length} in
          </div>
        </div>
      )}

      {/* Controls hint */}
      <div className="absolute bottom-3 right-3 text-[9px] font-mono z-10 pointer-events-none" style={{ color: P.dim }}>
        left drag: rotate · scroll: zoom · right drag: pan
      </div>
    </div>
  );
}
