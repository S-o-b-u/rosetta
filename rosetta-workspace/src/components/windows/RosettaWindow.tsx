"use client";

import React, { useCallback, useRef, useEffect, useState } from "react";
import type {
  WindowInstance,
  WindowManagerActions,
} from "@/components/windows/types";

// ── Constants ──
const MENUBAR_HEIGHT = 32; // h-8
const DOCK_HEIGHT = 80; // bottom dock clearance
const MIN_VISIBLE = 60; // minimum pixels visible when dragged near edge

interface RosettaWindowProps {
  window: WindowInstance;
  actions: WindowManagerActions;
  desktopRef: React.RefObject<HTMLDivElement | null>;
}

export function RosettaWindow({
  window: win,
  actions,
  desktopRef,
}: RosettaWindowProps) {
  const windowRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);
  const isResizing = useRef<string | null>(null);
  const dragStart = useRef({ x: 0, y: 0, winX: 0, winY: 0 });
  const resizeStart = useRef({ x: 0, y: 0, w: 0, h: 0, winX: 0, winY: 0 });
  const [isDraggingVisual, setIsDraggingVisual] = useState(false);

  const isActive =
    win.zIndex >= (actions.getTopZIndex?.() ?? 0) - 1; // approximate "top"
  const isMaximized = win.state === "maximized";

  // ── Compute maximized geometry ──
  const getMaxBounds = useCallback(() => {
    const desktop = desktopRef.current;
    if (!desktop) return { x: 0, y: 0, width: 800, height: 600 };
    const rect = desktop.getBoundingClientRect();
    return {
      x: 0,
      y: 0,
      width: rect.width,
      height: rect.height,
    };
  }, [desktopRef]);

  // ── Drag handlers ──
  const onDragStart = useCallback(
    (e: React.PointerEvent) => {
      if (isMaximized) return;
      // Don't drag if clicking a button
      if ((e.target as HTMLElement).closest("button")) return;

      e.preventDefault();
      e.stopPropagation();
      isDragging.current = true;
      setIsDraggingVisual(true);
      dragStart.current = {
        x: e.clientX,
        y: e.clientY,
        winX: win.position.x,
        winY: win.position.y,
      };

      actions.focusWindow(win.id);

      const onMove = (ev: PointerEvent) => {
        if (!isDragging.current) return;
        ev.preventDefault();

        const dx = ev.clientX - dragStart.current.x;
        const dy = ev.clientY - dragStart.current.y;

        let newX = dragStart.current.winX + dx;
        let newY = dragStart.current.winY + dy;

        // Constrain to desktop bounds
        const desktop = desktopRef.current;
        if (desktop) {
          const rect = desktop.getBoundingClientRect();
          const maxX = rect.width - MIN_VISIBLE;
          const maxY = rect.height - MIN_VISIBLE;
          newX = Math.max(-win.dimensions.width + MIN_VISIBLE, Math.min(newX, maxX));
          newY = Math.max(0, Math.min(newY, maxY));
        }

        actions.updatePosition(win.id, { x: newX, y: newY });
      };

      const onUp = () => {
        isDragging.current = false;
        setIsDraggingVisual(false);
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [win.id, win.position, win.dimensions.width, isMaximized, actions, desktopRef]
  );

  // ── Resize handlers ──
  const onResizeStart = useCallback(
    (edge: string) => (e: React.PointerEvent) => {
      if (isMaximized) return;
      e.preventDefault();
      e.stopPropagation();
      isResizing.current = edge;
      resizeStart.current = {
        x: e.clientX,
        y: e.clientY,
        w: win.dimensions.width,
        h: win.dimensions.height,
        winX: win.position.x,
        winY: win.position.y,
      };

      actions.focusWindow(win.id);

      const onMove = (ev: PointerEvent) => {
        if (!isResizing.current) return;
        ev.preventDefault();

        const dx = ev.clientX - resizeStart.current.x;
        const dy = ev.clientY - resizeStart.current.y;
        const dir = isResizing.current;

        let newW = resizeStart.current.w;
        let newH = resizeStart.current.h;

        if (dir.includes("right") || dir === "right") {
          newW = Math.max(win.minWidth, resizeStart.current.w + dx);
        }
        if (dir.includes("bottom") || dir === "bottom") {
          newH = Math.max(win.minHeight, resizeStart.current.h + dy);
        }

        actions.updateDimensions(win.id, { width: newW, height: newH });
      };

      const onUp = () => {
        isResizing.current = null;
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
      };

      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    },
    [win.id, win.dimensions, win.position, win.minWidth, win.minHeight, isMaximized, actions]
  );

  // ── Double-click title bar toggles maximize ──
  const onTitleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      actions.maximizeWindow(win.id);
    },
    [win.id, actions]
  );

  // ── Click to focus ──
  const onWindowPointerDown = useCallback(() => {
    actions.focusWindow(win.id);
  }, [win.id, actions]);

  // ── Compute position/size ──
  const maxBounds = getMaxBounds();
  const style: React.CSSProperties = isMaximized
    ? {
        position: "absolute",
        top: 0,
        left: 0,
        width: maxBounds.width,
        height: maxBounds.height,
        zIndex: win.zIndex,
      }
    : {
        position: "absolute",
        top: win.position.y,
        left: win.position.x,
        width: win.dimensions.width,
        height: win.dimensions.height,
        zIndex: win.zIndex,
      };

  // ── Traffic-light hover state ──
  const [controlsHovered, setControlsHovered] = useState(false);

  return (
    <div
      ref={windowRef}
      style={{
        ...style,
        transform: isDraggingVisual ? "scale(1.018)" : "scale(1)",
        transition: isDraggingVisual
          ? "box-shadow 0.15s ease"
          : "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s ease, opacity 0.2s ease",
        willChange: isDraggingVisual ? "transform" : "auto",
      }}
      onPointerDown={onWindowPointerDown}
      className={`flex flex-col overflow-hidden ${
        isMaximized ? "rounded-none" : "rounded-xl"
      } ${
        isDraggingVisual
          ? "shadow-[0_30px_60px_rgba(0,0,0,0.55),0_0_0_1px_rgba(255,255,255,0.08)]"
          : isActive
            ? "shadow-2xl shadow-black/60"
            : "shadow-lg shadow-black/40 opacity-95"
      }`}
    >
      {/* ── Title Bar ── */}
      <div
        onPointerDown={onDragStart}
        onDoubleClick={onTitleDoubleClick}
        className={`flex items-center h-9 px-3 shrink-0 ${
          isMaximized ? "" : "cursor-grab active:cursor-grabbing"
        } ${
          isActive
            ? "bg-neutral-900/95 border-b border-white/[0.08]"
            : "bg-neutral-900/80 border-b border-white/[0.05]"
        }`}
        style={{ touchAction: "none", userSelect: "none" }}
      >
        {/* Traffic lights */}
        <div
          className="flex items-center gap-[7px] mr-3"
          onMouseEnter={() => setControlsHovered(true)}
          onMouseLeave={() => setControlsHovered(false)}
        >
          {/* Close */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              actions.closeWindow(win.id);
            }}
            className={`w-[13px] h-[13px] rounded-full transition-colors duration-150 flex items-center justify-center ${
              controlsHovered
                ? "bg-red-500 hover:bg-red-400"
                : "bg-zinc-600/80"
            }`}
            title="Close"
          >
            {controlsHovered && (
              <svg width="8" height="8" viewBox="0 0 8 8">
                <path
                  d="M1 1l6 6M7 1l-6 6"
                  stroke="rgba(0,0,0,0.6)"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>

          {/* Minimize */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              actions.minimizeWindow(win.id);
            }}
            className={`w-[13px] h-[13px] rounded-full transition-colors duration-150 flex items-center justify-center ${
              controlsHovered
                ? "bg-yellow-500 hover:bg-yellow-400"
                : "bg-zinc-600/80"
            }`}
            title="Minimize"
          >
            {controlsHovered && (
              <svg width="8" height="8" viewBox="0 0 8 8">
                <path
                  d="M1.5 4h5"
                  stroke="rgba(0,0,0,0.6)"
                  strokeWidth="1.4"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </button>

          {/* Maximize */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              actions.maximizeWindow(win.id);
            }}
            className={`w-[13px] h-[13px] rounded-full transition-colors duration-150 flex items-center justify-center ${
              controlsHovered
                ? "bg-green-500 hover:bg-green-400"
                : "bg-zinc-600/80"
            }`}
            title={isMaximized ? "Restore" : "Maximize"}
          >
            {controlsHovered && (
              <svg width="8" height="8" viewBox="0 0 8 8">
                {isMaximized ? (
                  <>
                    <rect
                      x="1.5"
                      y="2.5"
                      width="3.5"
                      height="3.5"
                      fill="none"
                      stroke="rgba(0,0,0,0.6)"
                      strokeWidth="1.1"
                      rx="0.5"
                    />
                    <rect
                      x="3"
                      y="1"
                      width="3.5"
                      height="3.5"
                      fill="none"
                      stroke="rgba(0,0,0,0.6)"
                      strokeWidth="1.1"
                      rx="0.5"
                    />
                  </>
                ) : (
                  <path
                    d="M1 3.5L3.5 1L6 3.5M1 4.5L3.5 7L6 4.5"
                    stroke="rgba(0,0,0,0.6)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                  />
                )}
              </svg>
            )}
          </button>
        </div>

        {/* Window title */}
        <span
          className={`text-[12px] font-medium tracking-wide truncate ${
            isActive ? "text-zinc-200" : "text-zinc-500"
          }`}
        >
          {win.title}
        </span>
      </div>

      {/* ── Content Area ── */}
      <div
        className={`flex-1 overflow-auto ${
          isActive
            ? "bg-neutral-950/90 backdrop-blur-sm"
            : "bg-neutral-950/80"
        }`}
      >
        {win.content}
      </div>

      {/* ── Resize Handles (only when not maximized) ── */}
      {!isMaximized && (
        <>
          {/* Right edge */}
          <div
            onPointerDown={onResizeStart("right")}
            className="absolute top-0 right-0 w-1.5 h-full cursor-ew-resize z-10"
            style={{ touchAction: "none" }}
          />
          {/* Bottom edge */}
          <div
            onPointerDown={onResizeStart("bottom")}
            className="absolute bottom-0 left-0 h-1.5 w-full cursor-ns-resize z-10"
            style={{ touchAction: "none" }}
          />
          {/* Bottom-right corner */}
          <div
            onPointerDown={onResizeStart("bottom-right")}
            className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize z-20"
            style={{ touchAction: "none" }}
          />
        </>
      )}

      {/* ── Subtle border overlay ── */}
      <div
        className={`absolute inset-0 pointer-events-none ${
          isMaximized ? "" : "rounded-lg"
        } border ${
          isActive ? "border-white/[0.1]" : "border-white/[0.05]"
        }`}
      />
    </div>
  );
}
