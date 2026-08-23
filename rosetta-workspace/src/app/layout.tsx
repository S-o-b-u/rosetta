import type { Metadata } from "next";
import { Poppins, Geist_Mono } from "next/font/google";
import "./globals.css";

const poppins = Poppins({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Rosetta Workspace",
  description: "Rosetta Developer Operating Environment",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${poppins.variable} ${geistMono.variable} dark h-full antialiased font-sans`}
    >
      <body className="min-h-full flex flex-col font-sans bg-black text-white">
        {/* Global liquid glass SVG filter — referenced by url(#glass-blur) */}
        <svg className="hidden absolute" aria-hidden="true">
          <defs>
            <filter id="glass-blur" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
              <feTurbulence type="fractalNoise" baseFrequency="0.003 0.007" numOctaves="1" result="turbulence" />
              <feDisplacementMap in="SourceGraphic" in2="turbulence" scale="120" xChannelSelector="R" yChannelSelector="G" />
            </filter>
          </defs>
        </svg>
        {children}
      </body>
    </html>
  );
}
