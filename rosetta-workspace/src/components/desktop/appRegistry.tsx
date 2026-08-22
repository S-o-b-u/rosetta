"use client";

import React from "react";
import {
  IconTerminal2,
  IconBraces,
  IconTopologyStar3,
} from "@tabler/icons-react";
import type { WindowDefinition } from "@/components/windows/types";

// ── Application definition ──
export interface RosettaApp {
  id: string;
  title: string;
  icon: React.ReactNode;
  defaultWidth: number;
  defaultHeight: number;
  defaultPosition: { x: number; y: number };
  content: React.ReactNode;
}

// ── Helper: create a WindowDefinition from an app ──
export function appToWindowDef(app: RosettaApp): WindowDefinition {
  return {
    id: app.id,
    title: app.title,
    initialPosition: app.defaultPosition,
    initialWidth: app.defaultWidth,
    initialHeight: app.defaultHeight,
    content: app.content,
  };
}

// ── Placeholder content factory ──
function PlaceholderContent({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center space-y-2">
        <div className="text-zinc-200 text-base font-semibold tracking-tight">
          {title}
        </div>
        <div className="text-zinc-500 text-xs">{subtitle}</div>
      </div>
    </div>
  );
}

// ── Registered applications ──
export const appRegistry: RosettaApp[] = [
  {
    id: "cli",
    title: "Rosetta CLI",
    icon: (
      <IconTerminal2 className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 720,
    defaultHeight: 460,
    defaultPosition: { x: 80, y: 40 },
    content: (
      <PlaceholderContent
        title="Rosetta CLI"
        subtitle="Migration command interface will appear here."
      />
    ),
  },
  {
    id: "ast",
    title: "AST Explorer",
    icon: (
      <IconBraces className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 760,
    defaultHeight: 500,
    defaultPosition: { x: 160, y: 60 },
    content: (
      <PlaceholderContent
        title="AST Explorer"
        subtitle="AST processing surface will appear here."
      />
    ),
  },
  {
    id: "graph",
    title: "Knowledge Graph",
    icon: (
      <IconTopologyStar3 className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 800,
    defaultHeight: 520,
    defaultPosition: { x: 240, y: 80 },
    content: (
      <PlaceholderContent
        title="Knowledge Graph"
        subtitle="Graph visualization will appear here."
      />
    ),
  },
];

// ── Lookup helper ──
export function getAppById(id: string): RosettaApp | undefined {
  return appRegistry.find((app) => app.id === id);
}
