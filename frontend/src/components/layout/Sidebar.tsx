"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  label:    string;
  icon:     string;
  href:     string;
  external?: boolean;
  children?: NavItem[];
}

interface NavGroup {
  group: string | null;
  items: NavItem[];
}

const NAV_ITEMS: NavGroup[] = [
  {
    group: null,
    items: [
      { label: "Cockpit", icon: "cockp", href: "/cockpit", external: false },
    ],
  },
  {
    group: "TRADING",
    items: [
      { label: "Dashboard",     icon: "chart", href: "/dashboard",        external: false },
      { label: "Trade Mgmt",   icon: "trade", href: "/trade-management", external: false },
    ],
  },
  {
    group: "AGENTS",
    items: [
      { 
        label: "Paper Trading", 
        icon: "paper", 
        href: "/paper-trading", 
        external: false 
      },
      { 
        label: "Scalper",  
        icon: "scalp", 
        href: "/scalper",       
        external: false 
      },
      { 
        label: "Worker",    
        icon: "workr", 
        href: "/worker",        
        external: false 
      },
      { 
        label: "Multi-Agents", 
        icon: "agent", 
        href: "/agents",        
        external: false 
      },
    ],
  },
  {
    group: "BROKER",
    items: [
      { label: "Binance Real", icon: "broker", href: "/broker", external: false },
    ],
  },
  {
    group: "ANÁLISE",
    items: [
      { label: "Analytics",       icon: "analy", href: "/analytics",  external: false },
      { label: "Alpha Discovery", icon: "alpha", href: "/alpha",       external: false },
      { label: "Robustness",      icon: "robus", href: "/robustness",  external: false },
      { label: "Strategy Lab",    icon: "strat", href: "/strategies",  external: false },
    ],
  },
  {
    group: "SOCIAL",
    items: [
      { label: "Influencer",  icon: "influ", href: "/influencer", external: false },
    ],
  },
  {
    group: "SISTEMA",
    items: [
      { label: "API Docs", icon: "apido", href: "http://localhost:8000/docs", external: true },
    ],
  },
];

const ICON_MAP: Record<string, string> = {
  cockp: "🎛",
  chart: "◈",
  trade: "◉",
  paper: "◎",
  scalp: "⚡",
  workr: "⚙",
  agent: "⊞",
  broker: "🏦",
  analy: "▲",
  alpha: "◆",
  robus: "◇",
  strat: "⬡",
  influ: "★",
  apido: "⊞",
};

export default function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  const isGroupActive = (items: NavItem[]) => {
    return items.some(item => isActive(item.href));
  };

  return (
    <aside
      className="fixed inset-y-0 left-0 z-40 flex flex-col"
      style={{ width: "240px", background: "#050816", borderRight: "1px solid #1a2a4a" }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 px-4 h-14 border-b" style={{ borderColor: "#1a2a4a" }}>
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold text-white"
          style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}
        >
          T
        </div>
        <div className="leading-none">
          <div className="text-sm font-bold text-white tracking-wide">TradeAI</div>
          <div className="text-[9px] text-text-dim tracking-widest mt-0.5">AI TRADING COCKPIT</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {NAV_ITEMS.map(({ group, items }) => (
          <div key={group ?? "__root"} className="mb-1">
            {group && (
              <div className="px-3 pt-3 pb-1.5 text-[9px] font-semibold tracking-widest text-text-dim uppercase">
                {group}
              </div>
            )}
            {items.map(({ label, icon, href, external, children }) => {
              const active = isActive(href);
              const iconChar = ICON_MAP[icon] || icon;
              const hasChildren = children && children.length > 0;
              const groupActive = hasChildren ? isGroupActive(children) : active;

              if (external) {
                return (
                  <a
                    key={href}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 px-3 py-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-white/2 transition-all text-xs"
                  >
                    <span className="text-sm w-4 text-center shrink-0 opacity-60">{iconChar}</span>
                    <span>{label}</span>
                    <span className="ml-auto text-[9px] text-text-dim">ext</span>
                  </a>
                );
              }

              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs transition-all border-l-2 pl-[10px] ${
                    active
                      ? "bg-neon-blue/10 text-neon-blue border-neon-blue"
                      : "text-text-secondary hover:text-text-primary hover:bg-white/2 border-transparent"
                  }`}
                >
                  <span className={`text-sm w-4 text-center shrink-0 ${active ? "text-neon-blue" : "opacity-50"}`}>
                    {iconChar}
                  </span>
                  <span className={active ? "font-medium" : ""}>{label}</span>
                  {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-neon-blue shrink-0" />}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t" style={{ borderColor: "#1a2a4a" }}>
        <div className="text-[9px] text-text-dim leading-relaxed font-mono">
          <div>v14.0.0 — Fase 14</div>
          <div>Quantitative Platform</div>
        </div>
      </div>
    </aside>
  );
}