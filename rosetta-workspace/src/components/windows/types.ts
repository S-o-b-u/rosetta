import React from "react";

// ── Window state machine ──
export type WindowState = "normal" | "minimized" | "maximized" | "closed";

// ── Position & dimensions ──
export interface WindowPosition {
  x: number;
  y: number;
}

export interface WindowDimensions {
  width: number;
  height: number;
}

// ── Window definition (used to register a new window) ──
export interface WindowDefinition {
  id: string;
  title: string;
  initialPosition?: WindowPosition;
  initialWidth?: number;
  initialHeight?: number;
  minWidth?: number;
  minHeight?: number;
  content: React.ReactNode;
}

// ── Live window instance (managed by WindowManager) ──
export interface WindowInstance {
  id: string;
  title: string;
  position: WindowPosition;
  dimensions: WindowDimensions;
  minWidth: number;
  minHeight: number;
  zIndex: number;
  state: WindowState;
  content: React.ReactNode;
  /** Snapshot before maximize, used for restore */
  preMaximize: {
    position: WindowPosition;
    dimensions: WindowDimensions;
  } | null;
}

// ── Actions exposed by the WindowManager context ──
export interface WindowManagerActions {
  openWindow: (def: WindowDefinition) => void;
  closeWindow: (id: string) => void;
  minimizeWindow: (id: string) => void;
  maximizeWindow: (id: string) => void;
  restoreWindow: (id: string) => void;
  focusWindow: (id: string) => void;
  updatePosition: (id: string, pos: WindowPosition) => void;
  updateDimensions: (id: string, dims: WindowDimensions) => void;
  getTopZIndex: () => number;
  /**
   * Smart dock launch: opens, focuses, or restores depending on current state.
   * Accepts a WindowDefinition so the caller provides content.
   */
  launchApp: (def: WindowDefinition) => void;
}

// ── Helper to query a window by id ──
export function getWindowState(
  windows: WindowInstance[],
  id: string
): WindowState | "not-open" {
  const win = windows.find((w) => w.id === id);
  return win ? win.state : "not-open";
}

export interface WindowManagerContextValue {
  windows: WindowInstance[];
  actions: WindowManagerActions;
}
