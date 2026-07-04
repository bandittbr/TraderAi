"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  label:    string;
  icon:     string;
  href:     string;
  external: boolean;
}

interface NavGroup {
  group: string | null;
  items: NavItem[];
}

const NAV_ITEMS: NavGroup[] = [
  {
    group: null,
    items: [
      { label: "Control Center", icon: "\u2302", href: "/", external: false },
    ],
  },
  {
    group: "TRADING",
    items: [
      { label: "Dashboard",     icon: "\u25c8", href: "/dashboard",        external: false },
      { label: "Paper Trading", icon: "\u25ce", href: "/paper-trading",    external: false },
      { label: "Trade Mgmt",   icon: "\u25c9", href: "/trade-management", external: false },
      { label: "Scalper",      icon: "\u26a1", href: "/scalper",          external: false },
    ],
  },
  {
    group: "ANALISE",
    items: [
      { label: "Analytics",       icon: "\u25b2", href: "/analytics",  external: false },
      { label: "Alpha Discovery", icon: "\u25c6", href: "/alpha",       external: false },
      { label: "Robustness",      icon: "\u25c7", href: "/robustness",  external: false },
      { label: "Strategy Lab",    icon: "\u2b21", href: "/strategies", external: false },
    ],
  },
  {
    group: "SISTEMA",
    items: [
      { label: "API Docs", icon: "\u229e", href: "http://localhost:8000/docs", external: true },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  return (
    <aside
      className="fixed inset-y-0 left-0 z-40 flex flex-col"
      style={{ width: "220px", background: "#080c14", borderRight: "1px solid #141c2e" }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-[#141c2e] shrink-0">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold text-white"
          style={{ background: "linear-gradient(135deg, #2563eb, #7c3aed)" }}
        >
          T
        </div>
        <div className="leading-none">
          <div className="text-sm font-bold text-white tracking-wide">TradeAI</div>
          <div className="text-[9px] text-[#3b4a6b] tracking-widest mt-0.5">QUANT PLATFORM</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_ITEMS.map(({ group, items }) => (
          <div key={group ?? "__root"} className="mb-1">
            {group && (
              <div className="px-3 pt-3 pb-1.5 text-[9px] font-semibold tracking-widest text-[#2d3d5a]">
                {group}
              </div>
            )}
            {items.map(({ label, icon, href, external }) => {
              const active = isActive(href);
              if (external) {
                return (
                  <a
                    key={href}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-[#4a6080] hover:text-[#8aa4c8] hover:bg-[#0d1525] transition-all text-xs"
                  >
                    <span className="text-sm w-4 text-center shrink-0 opacity-60">{icon}</span>
                    <span>{label}</span>
                    <span className="ml-auto text-[9px] text-[#2d3d5a]">externallink</span>
                  </a>
                );
              }
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs transition-all border-l-2 pl-[10px] ${
                    active
                      ? "bg-blue-600/15 text-blue-300 border-blue-500"
                      : "text-[#4a6080] hover:text-[#8aa4c8] hover:bg-[#0d1525] border-transparent"
                  }`}
                >
                  <span className={`text-sm w-4 text-center shrink-0 ${active ? "text-blue-400" : "opacity-50"}`}>
                    {icon}
                  </span>
                  <span className={active ? "font-medium" : ""}>{label}</span>
                  {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[#141c2e] shrink-0">
        <div className="text-[9px] text-[#1e2e45] leading-relaxed font-mono">
          <div>v12.0.0 - Fase 12</div>
          <div>Quantitative Platform</div>
        </div>
      </div>
    </aside>
  );
}
