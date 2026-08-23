"use client";

import React, { useRef, useMemo, useState, useCallback, useEffect } from 'react';
import { RosettaMenubar } from './RosettaMenubar';
import { WindowManager, useWindowManager } from './WindowManager';
import { FloatingDock } from '@/components/ui/floating-dock';
import { appRegistry, appToWindowDef, getAppById } from './appRegistry';
import { getWindowState } from '@/components/windows/types';
import { DynamicIsland } from './DynamicIsland';

// ── Canvas pan offset state ──
interface PanState {
  x: number;
  y: number;
}

function DockContainer() {
  const { windows, actions } = useWindowManager();

  const maxZIndex = windows.length > 0
    ? Math.max(...windows.map(w => w.zIndex))
    : -1;

  const dockItems = useMemo(() => {
    const activeAppIds = ['cli', 'ast', 'graph', 'parity'];

    return activeAppIds.map(appId => {
      const app = getAppById(appId);
      if (!app) throw new Error(`App ${appId} not found in registry`);

      const state = getWindowState(windows, appId);
      const isFocused = (state === 'normal' || state === 'maximized') &&
        windows.find(w => w.id === appId)?.zIndex === maxZIndex;

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
  const [pan, setPan] = useState<PanState>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState<number>(1);
  const isPanning = useRef(false);
  const panStart = useRef({ mx: 0, my: 0, px: 0, py: 0 });
  const [isPanningVisual, setIsPanningVisual] = useState(false);

  // Handle zoom via wheel event
  useEffect(() => {
    const el = desktopRef.current;
    if (!el) return;

    const handleWheel = (e: WheelEvent) => {
      // Allow zooming with Ctrl/Cmd or normal scroll depending on preference, but here we'll just use any wheel event on the desktop background
      const target = e.target as HTMLElement;
      const isWindow = target.closest('[data-window]');
      // If we're scrolling inside a window, let it scroll normally unless Ctrl is pressed
      if (isWindow && !e.ctrlKey && !e.metaKey) return;
      
      e.preventDefault();
      
      setZoom(prevZoom => {
        // Adjust zoom speed
        const zoomDelta = e.deltaY * -0.002;
        const newZoom = prevZoom + zoomDelta;
        // Clamp between 0.2 and 2.0
        return Math.min(Math.max(newZoom, 0.2), 2.0);
      });
    };

    el.addEventListener('wheel', handleWheel, { passive: false });
    return () => el.removeEventListener('wheel', handleWheel);
  }, []);

  // Middle-mouse or space+drag to pan the infinite canvas
  const onDesktopPointerDown = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    // Only pan on middle mouse (button 1) or if clicking bare desktop (not a window)
    const target = e.target as HTMLElement;
    const isWindow = target.closest('[data-window]');
    const isDock = target.closest('[data-dock]');
    const isMenubar = target.closest('[data-menubar]');
    if (isWindow || isDock || isMenubar) return;

    // Left click on bare desktop also pans
    if (e.button === 0 || e.button === 1) {
      e.preventDefault();
      isPanning.current = true;
      setIsPanningVisual(true);
      panStart.current = { mx: e.clientX, my: e.clientY, px: pan.x, py: pan.y };

      const onMove = (ev: PointerEvent) => {
        if (!isPanning.current) return;
        const dx = ev.clientX - panStart.current.mx;
        const dy = ev.clientY - panStart.current.my;
        setPan({ x: panStart.current.px + dx, y: panStart.current.py + dy });
      };

      const onUp = () => {
        isPanning.current = false;
        setIsPanningVisual(false);
        document.removeEventListener('pointermove', onMove);
        document.removeEventListener('pointerup', onUp);
      };

      document.addEventListener('pointermove', onMove);
      document.addEventListener('pointerup', onUp);
    }
  }, [pan]);

  return (
    <div
      ref={desktopRef}
      data-desktop
      className="relative w-full h-screen overflow-hidden flex flex-col font-sans select-none"
      style={{
        backgroundImage: "url('/wallpaper/rosetta-bg.png')",
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        cursor: isPanningVisual ? 'grabbing' : 'default',
      }}
      onPointerDown={onDesktopPointerDown}
    >
      <div className="absolute inset-0 bg-black/25 pointer-events-none" />

      <RosettaMenubar />
      <DynamicIsland />

      {/* Infinite canvas — all windows live inside this translate/scale layer */}
      <WindowManager desktopRef={desktopRef} canvasOffset={pan} zoom={zoom}>
        <DockContainer />
      </WindowManager>

      {/* Subtle grid dots overlay to convey infinite canvas feel */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.04]"
        style={{
          backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.6) 1px, transparent 1px)',
          backgroundSize: `${32 * zoom}px ${32 * zoom}px`,
          backgroundPosition: `${pan.x % (32 * zoom)}px ${pan.y % (32 * zoom)}px`,
        }}
      />
    </div>
  );
}
