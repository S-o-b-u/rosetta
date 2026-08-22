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
  bg: "#070b14",
  nodePrimary: "#58a6ff",
  nodeSecondary: "#56d4dd",
  edgeColor: "#1a3a5c",
  labelText: "#e6edf3",
  dim: "#3b4252",
  green: "#3fb950",
  purple: "#bc8cff",
};

/* ── Legend ── */
function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-2 h-2 rounded-full"
        style={{ background: color, boxShadow: `0 0 8px ${color}60` }}
      />
      <span className="text-[10px] font-mono" style={{ color: "#6b7280" }}>
        {label}
      </span>
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
        if (width > 0 && height > 0) setDims({ w: Math.floor(width), h: Math.floor(height) });
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
        label: n.label,
        isTarget: n.id === targetId,
        val: n.id === targetId ? 10 : 5,
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

      const radius = isTarget ? 5 : 3.5;
      const color = isTarget ? P.nodePrimary : P.nodeSecondary;

      // Core sphere — PBR material
      const geo = new THREE.SphereGeometry(radius, 64, 64);
      const mat = new THREE.MeshStandardMaterial({
        color: new THREE.Color(color),
        emissive: new THREE.Color(color),
        emissiveIntensity: isHov ? 0.6 : 0.2,
        roughness: 0.25,
        metalness: 0.6,
        transparent: true,
        opacity: isHov ? 1.0 : 0.9,
      });
      group.add(new THREE.Mesh(geo, mat));

      // Outer glow sphere
      const glowGeo = new THREE.SphereGeometry(radius * 1.6, 32, 32);
      const glowMat = new THREE.MeshBasicMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: isHov ? 0.12 : 0.04,
        side: THREE.BackSide,
      });
      group.add(new THREE.Mesh(glowGeo, glowMat));

      // Text label sprite — retina-quality
      const scale = 2; // retina
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d")!;
      const fontSize = (isTarget ? 26 : 20) * scale;
      const text = node.id;
      ctx.font = `600 ${fontSize}px "Inter", "SF Pro", system-ui, sans-serif`;
      const tm = ctx.measureText(text);
      const pad = 16 * scale;
      const cw = tm.width + pad * 2;
      const ch = fontSize + pad * 1.4;
      canvas.width = cw;
      canvas.height = ch;

      // Background pill
      ctx.fillStyle = "rgba(7, 11, 20, 0.82)";
      const r = (ch / 2);
      ctx.beginPath();
      ctx.roundRect(0, 0, cw, ch, r);
      ctx.fill();

      // Border
      ctx.strokeStyle = `${color}40`;
      ctx.lineWidth = 1.5 * scale;
      ctx.beginPath();
      ctx.roundRect(0, 0, cw, ch, r);
      ctx.stroke();

      // Text
      ctx.fillStyle = isTarget ? P.nodePrimary : P.labelText;
      ctx.font = `600 ${fontSize}px "Inter", "SF Pro", system-ui, sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(text, cw / 2, ch / 2);

      const tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      const spriteMat = new THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        depthWrite: false,
      });
      const sprite = new THREE.Sprite(spriteMat);
      const spriteScale = 0.045;
      sprite.scale.set(cw * spriteScale, ch * spriteScale, 1);
      sprite.position.set(0, radius + 4, 0);
      group.add(sprite);

      return group;
    },
    [hovered]
  );

  // ── Scene post-processing ──
  const onEngineInit = useCallback((fg: any) => {
    if (!fg) return;
    const scene = fg.scene();
    const THREE = require("three");

    // Remove any existing custom lights (prevent duplicates)
    const toRemove: any[] = [];
    scene.traverse((child: any) => {
      if (child.userData?.__rosetta_light) toRemove.push(child);
    });
    toRemove.forEach((l: any) => scene.remove(l));

    // Ambient
    const ambient = new THREE.AmbientLight(0xffffff, 0.4);
    ambient.userData.__rosetta_light = true;
    scene.add(ambient);

    // Main directional
    const dir = new THREE.DirectionalLight(0x58a6ff, 0.8);
    dir.position.set(50, 80, 60);
    dir.userData.__rosetta_light = true;
    scene.add(dir);

    // Back fill
    const fill = new THREE.DirectionalLight(0x56d4dd, 0.3);
    fill.position.set(-40, -30, -50);
    fill.userData.__rosetta_light = true;
    scene.add(fill);

    // Subtle bottom glow
    const bottom = new THREE.PointLight(0xbc8cff, 0.2, 200);
    bottom.position.set(0, -60, 0);
    bottom.userData.__rosetta_light = true;
    scene.add(bottom);

    // Scene background
    scene.background = new THREE.Color(P.bg);

    // Camera position
    fg.cameraPosition({ x: 0, y: 0, z: 120 });
  }, []);

  // ── Fit camera after data ──
  useEffect(() => {
    if (fgRef.current && graphData.nodes.length > 0) {
      const t = setTimeout(() => {
        onEngineInit(fgRef.current);
        fgRef.current?.zoomToFit?.(800, 50);
      }, 600);
      return () => clearTimeout(t);
    }
  }, [graphData, onEngineInit]);

  // ── Auto-rotate ──
  useEffect(() => {
    if (!fgRef.current || graphData.nodes.length === 0) return;
    let frame: number;
    const rotate = () => {
      if (fgRef.current) {
        const scene = fgRef.current.scene();
        if (scene) scene.rotation.y += 0.0008;
      }
      frame = requestAnimationFrame(rotate);
    };
    frame = requestAnimationFrame(rotate);
    return () => cancelAnimationFrame(frame);
  }, [graphData]);

  // ── Empty state ──
  if (!neo4jContext || graphData.nodes.length === 0) {
    return (
      <div
        className="flex flex-col items-center justify-center h-full font-mono gap-4"
        style={{ background: P.bg }}
      >
        <div className="w-16 h-16 rounded-2xl border border-white/5 flex items-center justify-center bg-white/[0.02]">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#3b4252" strokeWidth="1.5">
            <circle cx="12" cy="5" r="2" />
            <circle cx="5" cy="19" r="2" />
            <circle cx="19" cy="19" r="2" />
            <line x1="12" y1="7" x2="5" y2="17" />
            <line x1="12" y1="7" x2="19" y2="17" />
          </svg>
        </div>
        <div className="text-[13px] font-medium" style={{ color: "#4b5563" }}>
          Knowledge Graph
        </div>
        <div className="text-[11px]" style={{ color: "#374151" }}>
          Run a migration to visualize dependencies
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full overflow-hidden"
      style={{ background: P.bg }}
    >
      <ForceGraph3D
        ref={fgRef}
        graphData={graphData}
        width={dims.w}
        height={dims.h}
        backgroundColor={P.bg}
        showNavInfo={false}
        // Nodes
        nodeThreeObject={nodeThreeObject}
        nodeThreeObjectExtend={false}
        // Links
        linkColor={() => P.edgeColor}
        linkWidth={2}
        linkOpacity={0.5}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={0.85}
        linkDirectionalArrowColor={() => P.nodeSecondary + "80"}
        linkDirectionalParticles={3}
        linkDirectionalParticleWidth={1.2}
        linkDirectionalParticleColor={() => P.nodePrimary}
        linkDirectionalParticleSpeed={0.005}
        // Interaction
        onNodeHover={(n: any) => setHovered(n?.id ?? null)}
        // Forces
        d3AlphaDecay={0.03}
        d3VelocityDecay={0.25}
        warmupTicks={50}
        cooldownTicks={100}
      />

      {/* HUD */}
      <div className="absolute top-4 left-4 z-10 pointer-events-none">
        <div className="text-[14px] font-semibold font-mono" style={{ color: P.labelText }}>
          Knowledge Graph
        </div>
        <div className="text-[11px] font-mono mt-0.5" style={{ color: P.dim }}>
          {graphData.nodes.length} services · {graphData.links.length} dependencies
        </div>
      </div>

      {/* Legend */}
      <div
        className="absolute bottom-4 left-4 flex flex-col gap-1 px-3 py-2 rounded-xl z-10 pointer-events-none"
        style={{
          background: "rgba(7,11,20,0.85)",
          border: "1px solid rgba(255,255,255,0.05)",
          backdropFilter: "blur(12px)",
        }}
      >
        <LegendDot color={P.nodePrimary} label="Target" />
        <LegendDot color={P.nodeSecondary} label="Dependency" />
        <LegendDot color={P.purple} label="CALLS" />
      </div>

      {/* Hover tooltip */}
      {hovered && (
        <div
          className="absolute top-4 right-4 px-3 py-2 rounded-xl font-mono text-[12px] z-10 pointer-events-none"
          style={{
            background: "rgba(7,11,20,0.92)",
            border: `1px solid ${P.nodePrimary}30`,
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{ color: P.nodePrimary }} className="font-semibold">
            {hovered}
          </div>
          <div className="text-[10px] mt-1" style={{ color: P.dim }}>
            {graphData.links.filter(
              (l: any) => (l.source === hovered || l.source?.id === hovered)
            ).length}{" "}
            out ·{" "}
            {graphData.links.filter(
              (l: any) => (l.target === hovered || l.target?.id === hovered)
            ).length}{" "}
            in
          </div>
        </div>
      )}

      {/* Controls hint */}
      <div
        className="absolute bottom-4 right-4 text-[10px] font-mono z-10 pointer-events-none"
        style={{ color: P.dim }}
      >
        drag: rotate · scroll: zoom · right-drag: pan
      </div>
    </div>
  );
}
