"use client";

import React, { useEffect, useState } from 'react';
import {
  IconTerminal2,
  IconCpu,
  IconSearch,
  IconAdjustmentsHorizontal,
  IconLayersSubtract,
} from '@tabler/icons-react';

const menuItems = ['File', 'Edit', 'View', 'Go', 'Run', 'Terminal', 'Help'];

export function RosettaMenubar() {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const options: Intl.DateTimeFormatOptions = {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      };
      // e.g. "Sat, Aug 22, 3:52 PM"
      const formatted = now.toLocaleDateString('en-US', options).replace(',', '');
      setTimeStr(formatted);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-8 w-full bg-black/40 backdrop-blur-xl border-b border-white/[0.08] text-zinc-300 text-xs select-none shadow-sm flex items-center justify-between px-3 z-50 transition-colors">
      {/* Left side: Logo & Mac Menus */}
      <div className="flex items-center space-x-1">
        {/* Rosetta Core Symbol */}
        <button
          className="flex items-center gap-1.5 px-2 py-1 rounded-md text-zinc-100 hover:bg-white/10 transition-all font-semibold tracking-wider group"
          title="Rosetta System"
        >
          <div className="w-4 h-4 rounded-full bg-red-600/20 border border-red-500/40 flex items-center justify-center text-red-400 group-hover:scale-105 transition-transform">
            <IconLayersSubtract size={11} stroke={2.5} />
          </div>
          <span className="text-[12px] font-bold tracking-tight text-white">ROSETTA</span>
        </button>

        {/* Menu Items */}
        <nav className="flex items-center space-x-0.5 text-zinc-300">
          {menuItems.map((item) => (
            <button
              key={item}
              className="px-2.5 py-1 rounded-md hover:bg-white/10 hover:text-white transition-colors duration-150 text-[12px] font-medium"
            >
              {item}
            </button>
          ))}
        </nav>
      </div>

      {/* Right side: Developer Symbolic Status & Realtime Mac Clock */}
      <div className="flex items-center space-x-2">
        {/* Rosetta Engine / Core Symbol */}
        <div
          className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.05] border border-white/[0.08] hover:bg-white/[0.1] text-zinc-300 hover:text-white cursor-pointer transition-all text-[11px]"
          title="Rosetta Engine: Active"
        >
          <IconCpu size={13} className="text-red-400" />
          <span className="font-mono text-[10px] text-zinc-300">v1.0</span>
        </div>

        {/* CLI Connection Status */}
        <div
          className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-950/40 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-900/40 cursor-pointer transition-all text-[11px]"
          title="CLI Connected: rosetta-cli daemon ready"
        >
          <IconTerminal2 size={13} className="text-emerald-400" />
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_6px_rgba(52,211,153,0.8)]" />
          <span className="font-medium text-[11px]">CLI</span>
        </div>

        {/* Spotlight / Command Search Symbol */}
        <button
          className="p-1 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          title="Rosetta Command Palette (⌘K)"
        >
          <IconSearch size={14} />
        </button>

        {/* Control Center Symbol */}
        <button
          className="p-1 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 transition-colors"
          title="System Control Center"
        >
          <IconAdjustmentsHorizontal size={14} />
        </button>

        {/* Real-time Clock */}
        <div className="px-2 py-0.5 rounded-md hover:bg-white/10 cursor-pointer transition-colors text-[12px] font-medium text-zinc-200 tracking-tight">
          {timeStr || 'Loading...'}
        </div>
      </div>
    </header>
  );
}
