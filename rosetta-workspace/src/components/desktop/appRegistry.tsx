"use client";

import React from "react";
import {
  IconTerminal2,
  IconBraces,
  IconTopologyStar3,
  IconScaleOutline,
} from "@tabler/icons-react";
import type { WindowDefinition } from "@/components/windows/types";

import { CliApp } from "./CliApp";
import { AstApp } from "./AstApp";
import { GraphApp } from "./GraphApp";
import { ParityHarness } from "./ParityHarness";

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

// ── Registered applications ──
export const appRegistry: RosettaApp[] = [
  {
    id: "cli",
    title: "Recast CLI",
    icon: (
      <IconTerminal2 className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 580,
    defaultHeight: 380,
    defaultPosition: { x: 60, y: 50 },
    content: <CliApp />,
  },
  {
    id: "ast",
    title: "AST Explorer",
    icon: (
      <IconBraces className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 620,
    defaultHeight: 420,
    defaultPosition: { x: 140, y: 70 },
    content: <AstApp />,
  },
  {
    id: "graph",
    title: "Knowledge Graph",
    icon: (
      <IconTopologyStar3 className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 660,
    defaultHeight: 440,
    defaultPosition: { x: 220, y: 90 },
    content: <GraphApp />,
  },
  {
    id: "parity",
    title: "Parity Harness",
    icon: (
      <IconScaleOutline className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 800,
    defaultHeight: 500,
    defaultPosition: { x: 300, y: 60 },
    content: <ParityHarness />,
  },
];

// ── Lookup helper ──
export function getAppById(id: string): RosettaApp | undefined {
  return appRegistry.find((app) => app.id === id);
}
