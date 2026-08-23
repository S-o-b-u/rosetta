"use client";

import React, { useEffect, useState } from 'react';
import { LiquidGlassCard } from '@/components/ui/liquid-glass';

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
      setTimeStr(now.toLocaleDateString('en-US', options).replace(',', ''));
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="absolute top-0 left-0 w-full h-12 pointer-events-none z-50 flex items-start justify-between px-4 pt-2">
      {/* Left side: Logo & Mac Menus */}
      <LiquidGlassCard
        draggable={false}
        expandable={false}
        blurIntensity="xl"
        glowIntensity="xs"
        shadowIntensity="xs"
        borderRadius="999px"
        className="pointer-events-auto"
        style={{ background: 'rgba(8,8,8,0.80)', border: '1px solid rgba(255,255,255,0.09)' }}
      >
        <div className="relative z-30 h-full px-4 py-1.5 flex items-center space-x-3">
          <div className="flex items-center gap-2 text-white hover:text-gray-300 transition-colors cursor-pointer pr-3 border-r border-white/10">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
            </svg>
            <span className="text-[12px] font-bold tracking-tight">RECAST</span>
          </div>

          <nav className="flex items-center space-x-0.5">
            {menuItems.map((item) => (
              <button
                key={item}
                className="px-3 py-1.5 rounded-full hover:bg-white/10 hover:text-white transition-colors text-[12px] font-medium text-[#A3A3A3]"
              >
                {item}
              </button>
            ))}
          </nav>
        </div>
      </LiquidGlassCard>

      {/* Right side: Minimal Status & Time */}
      <LiquidGlassCard
        draggable={false}
        expandable={false}
        blurIntensity="xl"
        glowIntensity="xs"
        shadowIntensity="xs"
        borderRadius="999px"
        className="pointer-events-auto"
        style={{ background: 'rgba(8,8,8,0.80)', border: '1px solid rgba(255,255,255,0.09)' }}
      >
        <div className="relative z-30 px-5 py-1.5 flex items-center space-x-4">
          <div className="flex items-center gap-2" title="CLI Connected">
            <div className="w-1.5 h-1.5 rounded-full bg-white" />
            <span className="font-medium text-[11px] text-white">CLI Ready</span>
          </div>

          <div className="text-[12px] font-medium text-white tracking-tight border-l border-white/10 pl-4">
            {timeStr || '...'}
          </div>
        </div>
      </LiquidGlassCard>
    </div>
  );
}
