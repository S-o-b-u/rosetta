"use client";

import React from "react";
import {
  IconTerminal2,
  IconBraces,
  IconTopologyStar3,
} from "@tabler/icons-react";
import type { WindowDefinition } from "@/components/windows/types";

import { CliApp } from "./CliApp";
import { AstApp } from "./AstApp";
import { GraphApp } from "./GraphApp";

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
    title: "Rosetta CLI",
    icon: (
      <IconTerminal2 className="h-full w-full text-zinc-300 hover:text-white transition-colors" />
    ),
    defaultWidth: 720,
    defaultHeight: 460,
    defaultPosition: { x: 80, y: 40 },
    content: <CliApp />,
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
    content: <AstApp />,
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
    content: <GraphApp />,
  },
];

// ── Lookup helper ──
export function getAppById(id: string): RosettaApp | undefined {
  return appRegistry.find((app) => app.id === id);
}
