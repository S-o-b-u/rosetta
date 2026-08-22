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

  return (
    <WindowManagerContext.Provider value={ctxValue}>
      {/* Desktop workspace area where windows live */}
      <div className="flex-1 relative z-10 overflow-hidden">
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
