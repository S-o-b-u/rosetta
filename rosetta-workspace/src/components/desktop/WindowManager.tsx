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
}: {
  children?: React.ReactNode;
  desktopRef: React.RefObject<HTMLDivElement | null>;
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

  // ── Pan / Zoom state ──
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const isPanning = useRef(false);
  const panStart = useRef({ x: 0, y: 0, panX: 0, panY: 0 });

  const onCanvasPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      // Only pan on Shift+click or middle-click on the background (not on a window)
      const target = e.target as HTMLElement;
      const isCanvas =
        target.getAttribute("data-canvas") === "true";
      if (!isCanvas) return;

      const isShiftClick = e.shiftKey && e.button === 0;
      const isMiddleClick = e.button === 1;
      if (!isShiftClick && !isMiddleClick) return;

      e.preventDefault();
      isPanning.current = true;
      panStart.current = {
        x: e.clientX,
        y: e.clientY,
        panX: panOffset.x,
        panY: panOffset.y,
      };

      const onMove = (ev: PointerEvent) => {
        if (!isPanning.current) return;
        ev.preventDefault();
        const dx = ev.clientX - panStart.current.x;
        const dy = ev.clientY - panStart.current.y;
        setPanOffset({
          x: panStart.current.panX + dx,
          y: panStart.current.panY + dy,
        });
      };

      const onUp = () => {
        isPanning.current = false;
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [panOffset]
  );

  const onCanvasWheel = useCallback(
    (e: React.WheelEvent<HTMLDivElement>) => {
      // Only zoom when Ctrl is held (pinch gesture)
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoom((prev) => {
        const delta = e.deltaY > 0 ? -0.05 : 0.05;
        return Math.min(1.5, Math.max(0.5, prev + delta));
      });
    },
    []
  );

  // Reset pan/zoom on double-click on empty canvas
  const onCanvasDoubleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const target = e.target as HTMLElement;
      if (target.getAttribute("data-canvas") !== "true") return;
      setPanOffset({ x: 0, y: 0 });
      setZoom(1);
    },
    []
  );

  return (
    <WindowManagerContext.Provider value={ctxValue}>
      {/* Desktop workspace area where windows live */}
      <div
        className="flex-1 relative z-10 overflow-hidden"
        onPointerDown={onCanvasPointerDown}
        onWheel={onCanvasWheel}
        onDoubleClick={onCanvasDoubleClick}
        style={{ cursor: isPanning.current ? "grabbing" : "default" }}
      >
        {/* Pannable / zoomable transform container */}
        <div
          data-canvas="true"
          className="absolute inset-0"
          style={{
            transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
            transformOrigin: "center center",
            transition: isPanning.current
              ? "none"
              : "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
          }}
        >
          {visibleWindows.map((win) => (
            <RosettaWindow
              key={win.id}
              window={win}
              actions={actions}
              desktopRef={desktopRef}
            />
          ))}
        </div>
      </div>
      {children}
    </WindowManagerContext.Provider>
  );
}

