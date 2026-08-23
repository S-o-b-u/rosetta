"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useState,
  useRef,
} from "react";
import type {
  WindowDefinition,
  WindowInstance,
  WindowManagerActions,
  WindowManagerContextValue,
  WindowPosition,
  WindowDimensions,
} from "@/components/windows/types";
import { RosettaWindow } from "@/components/windows/RosettaWindow";

// ── Clean Connection Threads ──
function WindowConnections({ windows }: { windows: WindowInstance[] }) {
  const getWin = (id: string) => windows.find((w) => w.id === id);
  const cli   = getWin("cli");
  const ast   = getWin("ast");
  const graph = getWin("graph");
  const parity = getWin("parity");

  const getPoints = (source: WindowInstance, target: WindowInstance, targetSide: 'left' | 'right' = 'left') => {
    const sx = source.position.x + source.dimensions.width;
    const sy = source.position.y + source.dimensions.height / 2;
    
    const tx = targetSide === 'left' ? target.position.x : target.position.x + target.dimensions.width;
    const ty = target.position.y + target.dimensions.height / 2;
    
    const dx = Math.max(Math.abs(tx - sx), 80);
    const c1x = sx + dx * 0.45;
    const c2x = targetSide === 'left' ? tx - dx * 0.45 : tx + dx * 0.45;
    
    const path = `M ${sx} ${sy} C ${c1x} ${sy}, ${c2x} ${ty}, ${tx} ${ty}`;
    return { path, sx, sy, tx, ty };
  };

  const connections: Array<{ src: WindowInstance; tgt: WindowInstance; id: string; targetSide?: 'left' | 'right' }> = [];
  if (cli   && ast)    connections.push({ src: cli,   tgt: ast,    id: "ca" });
  if (ast   && graph)  connections.push({ src: ast,   tgt: graph,  id: "ag" });
  if (graph && parity) connections.push({ src: graph, tgt: parity, id: "gp", targetSide: 'right' });

  const COLOR = "#ffffff"; // Crisp white

  return (
    <>
      <style>{`
        @keyframes flow-trail {
          from { stroke-dashoffset: 24; }
          to   { stroke-dashoffset: 0; }
        }
      `}</style>
      <svg
        className="absolute inset-0 pointer-events-none"
        style={{ width: "100%", height: "100%", overflow: "visible", zIndex: 5 }}
      >
        <defs>
          <marker id="clean-arrow" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto">
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill={COLOR} />
          </marker>
        </defs>

        {connections.map(({ src, tgt, id, targetSide }) => {
          const { path, sx, sy, tx, ty } = getPoints(src, tgt, targetSide);
          return (
            <g key={id}>
              {/* Ghost base line */}
              <path
                d={path}
                fill="none"
                stroke={COLOR}
                strokeOpacity={0.15}
                strokeWidth={2.5}
              />
              {/* Animated flowing trail */}
              <path
                d={path}
                fill="none"
                stroke={COLOR}
                strokeOpacity={0.8}
                strokeWidth={2.5}
                strokeDasharray="12 12"
                markerEnd="url(#clean-arrow)"
                style={{
                  animation: `flow-trail 0.6s linear infinite`,
                }}
              />
              {/* Source port */}
              <circle cx={sx} cy={sy} r={4} fill={COLOR} />
              {/* Target port */}
              <circle cx={tx} cy={ty} r={4} fill={COLOR} />
            </g>
          );
        })}
      </svg>
    </>
  );
}


// ── Context ──
const WindowManagerContext = createContext<WindowManagerContextValue | null>(
  null
);

export function useWindowManager(): WindowManagerContextValue {
  const ctx = useContext(WindowManagerContext);
  if (!ctx)
    throw new Error("useWindowManager must be used within WindowManager");
  return ctx;
}

// ── Constants ──
const BASE_Z = 100;

// ── WindowManager ──
export function WindowManager({
  children,
  desktopRef,
  canvasOffset = { x: 0, y: 0 },
  zoom = 1,
}: {
  children?: React.ReactNode;
  desktopRef: React.RefObject<HTMLDivElement | null>;
  canvasOffset?: { x: number; y: number };
  zoom?: number;
}) {
  const [windows, setWindows] = useState<WindowInstance[]>([]);
  const zCounter = useRef(BASE_Z);

  const nextZ = useCallback(() => {
    zCounter.current += 1;
    return zCounter.current;
  }, []);

  // ── Actions ──
  const openWindow = useCallback(
    (def: WindowDefinition) => {
      setWindows((prev) => {
        // Don't re-open if already exists and not closed
        const existing = prev.find((w) => w.id === def.id);
        if (existing && existing.state !== "closed") {
          // Just focus it
          const z = nextZ();
          return prev.map((w) =>
            w.id === def.id ? { ...w, zIndex: z, state: "normal" as const } : w
          );
        }
        // Remove closed instance if re-opening
        const filtered = prev.filter((w) => w.id !== def.id);
        const z = nextZ();
        const instance: WindowInstance = {
          id: def.id,
          title: def.title,
          position: def.initialPosition ?? { x: 120, y: 80 },
          dimensions: {
            width: def.initialWidth ?? 640,
            height: def.initialHeight ?? 440,
          },
          minWidth: def.minWidth ?? 320,
          minHeight: def.minHeight ?? 220,
          zIndex: z,
          state: "normal",
          content: def.content,
          preMaximize: null,
        };
        return [...filtered, instance];
      });
    },
    [nextZ]
  );

  const closeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, state: "closed" as const } : w))
    );
  }, []);

  const minimizeWindow = useCallback((id: string) => {
    setWindows((prev) =>
      prev.map((w) =>
        w.id === id ? { ...w, state: "minimized" as const } : w
      )
    );
  }, []);

  const maximizeWindow = useCallback(
    (id: string) => {
      setWindows((prev) =>
        prev.map((w) => {
          if (w.id !== id) return w;
          if (w.state === "maximized") {
            // Restore
            return {
              ...w,
              state: "normal" as const,
              position: w.preMaximize?.position ?? w.position,
              dimensions: w.preMaximize?.dimensions ?? w.dimensions,
              preMaximize: null,
              zIndex: nextZ(),
            };
          }
          // Maximize
          return {
            ...w,
            state: "maximized" as const,
            preMaximize: {
              position: { ...w.position },
              dimensions: { ...w.dimensions },
            },
            zIndex: nextZ(),
          };
        })
      );
    },
    [nextZ]
  );

  const restoreWindow = useCallback(
    (id: string) => {
      setWindows((prev) =>
        prev.map((w) => {
          if (w.id !== id) return w;
          if (w.state === "maximized") {
            return {
              ...w,
              state: "normal" as const,
              position: w.preMaximize?.position ?? w.position,
              dimensions: w.preMaximize?.dimensions ?? w.dimensions,
              preMaximize: null,
              zIndex: nextZ(),
            };
          }
          if (w.state === "minimized") {
            return { ...w, state: "normal" as const, zIndex: nextZ() };
          }
          return w;
        })
      );
    },
    [nextZ]
  );

  const focusWindow = useCallback(
    (id: string) => {
      const z = nextZ();
      setWindows((prev) =>
        prev.map((w) => (w.id === id ? { ...w, zIndex: z } : w))
      );
    },
    [nextZ]
  );

  const updatePosition = useCallback((id: string, pos: WindowPosition) => {
    setWindows((prev) =>
      prev.map((w) => (w.id === id ? { ...w, position: pos } : w))
    );
  }, []);

  const updateDimensions = useCallback(
    (id: string, dims: WindowDimensions) => {
      setWindows((prev) =>
        prev.map((w) => (w.id === id ? { ...w, dimensions: dims } : w))
      );
    },
    []
  );

  const getTopZIndex = useCallback(() => zCounter.current, []);

  /**
   * launchApp — the single entry point for dock icon clicks.
   * Behaviour:
   *   not-open / closed → openWindow (creates fresh)
   *   minimized         → restore then focus
   *   normal / maximized → focus (bring to front)
   */
  const launchApp = useCallback(
    (def: WindowDefinition) => {
      setWindows((prev) => {
        const existing = prev.find((w) => w.id === def.id);

        if (!existing || existing.state === "closed") {
          // Create new window
          const z = nextZ();
          const instance: WindowInstance = {
            id: def.id,
            title: def.title,
            position: def.initialPosition ?? { x: 120, y: 80 },
            dimensions: {
              width: def.initialWidth ?? 640,
              height: def.initialHeight ?? 440,
            },
            minWidth: def.minWidth ?? 320,
            minHeight: def.minHeight ?? 220,
            zIndex: z,
            state: "normal",
            content: def.content,
            preMaximize: null,
          };
          return [...prev.filter((w) => w.id !== def.id), instance];
        }

        if (existing.state === "minimized") {
          // Restore and focus
          const z = nextZ();
          return prev.map((w) =>
            w.id === def.id ? { ...w, state: "normal" as const, zIndex: z } : w
          );
        }

        // normal / maximized → just focus
        const z = nextZ();
        return prev.map((w) =>
          w.id === def.id ? { ...w, zIndex: z } : w
        );
      });
    },
    [nextZ]
  );

  const actions: WindowManagerActions = {
    openWindow,
    closeWindow,
    minimizeWindow,
    maximizeWindow,
    restoreWindow,
    focusWindow,
    updatePosition,
    updateDimensions,
    getTopZIndex,
    launchApp,
  };

  const ctxValue: WindowManagerContextValue = { windows, actions };

  // Only render visible (normal/maximized) windows
  const visibleWindows = windows.filter(
    (w) => w.state === "normal" || w.state === "maximized"
  );

  return (
    <WindowManagerContext.Provider value={ctxValue}>
      {/* Infinite canvas — windows are absolutely positioned inside, no clipping */}
      <div
        className="absolute inset-0 z-10"
        style={{
          transform: `translate(${canvasOffset.x}px, ${canvasOffset.y}px) scale(${zoom})`,
          transformOrigin: '0 0',
          willChange: 'transform',
          overflow: 'visible',
        }}
      >
        <WindowConnections windows={visibleWindows} />
        {visibleWindows.map((win) => (
          <RosettaWindow
            key={win.id}
            window={win}
            actions={actions}
            desktopRef={desktopRef}
          />
        ))}
      </div>
      {children}
    </WindowManagerContext.Provider>
  );
}
