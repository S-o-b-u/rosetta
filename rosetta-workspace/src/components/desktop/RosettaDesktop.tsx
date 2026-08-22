"use client";

import React, { useRef, useMemo } from 'react';
import { RosettaMenubar } from './RosettaMenubar';
import { WindowManager, useWindowManager } from './WindowManager';
import { FloatingDock } from '@/components/ui/floating-dock';
import { appRegistry, appToWindowDef, getAppById } from './appRegistry';
import { getWindowState } from '@/components/windows/types';
import { DynamicIsland } from './DynamicIsland';

function DockContainer() {
  const { windows, actions } = useWindowManager();

  // Find the max zIndex to determine which window is currently focused
  const maxZIndex = windows.length > 0 
    ? Math.max(...windows.map(w => w.zIndex)) 
    : -1;

  const dockItems = useMemo(() => {
    // For this step, we only register CLI, AST, and GRAPH for testing
    const activeAppIds = ['cli', 'ast', 'graph'];
    
    return activeAppIds.map(appId => {
      const app = getAppById(appId);
      if (!app) throw new Error(`App ${appId} not found in registry`);

      const state = getWindowState(windows, appId);
      const isFocused = (state === 'normal' || state === 'maximized') && 
        windows.find(w => w.id === appId)?.zIndex === maxZIndex;

      // Visual active indicator (macOS style dot below icon)
      const showIndicator = state !== 'closed' && state !== 'not-open';
      const indicatorClass = isFocused 
        ? "w-1 h-1 bg-zinc-200" 
        : "w-1 h-1 bg-zinc-500 opacity-60";

      return {
        title: app.title,
        href: "#",
        onClick: (e: React.MouseEvent) => {
          e.preventDefault();
          actions.launchApp(appToWindowDef(app));
        },
        icon: (
          <div className="relative flex items-center justify-center h-full w-full">
            {app.icon}
            {showIndicator && (
              <div className={`absolute -bottom-3 left-1/2 -translate-x-1/2 rounded-full transition-all duration-200 ${indicatorClass}`} />
            )}
          </div>
        ),
      };
    });
  }, [windows, actions, maxZIndex]);

  return (
    <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-50">
      <FloatingDock
        items={dockItems}
        desktopClassName="bg-neutral-950/80 dark:bg-neutral-950/85 backdrop-blur-2xl border border-white/[0.12] shadow-2xl shadow-black/70 rounded-3xl px-4 pb-3"
      />
    </div>
  );
}

export function RosettaDesktop() {
  const desktopRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={desktopRef}
      className="relative w-full h-screen overflow-hidden flex flex-col font-sans select-none"
      style={{
        backgroundImage: "url('/wallpaper/rosetta-bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
      }}
    >
      <div className="absolute inset-0 bg-black/25 pointer-events-none" />
      
      <RosettaMenubar />
      <DynamicIsland />

      <WindowManager desktopRef={desktopRef}>
        {/* Dock runs inside WindowManager so it can query window state & dispatch launches */}
        <DockContainer />
      </WindowManager>
    </div>
  );
}

