"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const ROUTE_LABELS: Record<string, string> = {
  "/":                 "Control Center",
  "/dashboard":        "Dashboard",
  "/paper-trading":    "Paper Trading",
  "/trade-management": "Trade Management",
  "/analytics":        "Analytics",
  "/alpha":            "Alpha Discovery",
  "/robustness":       "Robustness Engine",
  "/strategies":       "Strategy Lab",
  "/system-health":    "System Health",
  "/scalper":          "Scalper Engine",
};

type StatusLevel = "online" | "degraded" | "offline" | "loading";

interface SystemStatus {
  backend:  StatusLevel;
  lastSeen: string | null;
}

function StatusDot({ level }: { level: StatusLevel }) {
  const colors: Record<StatusLevel, string> = {
    online:   "bg-emerald-500",
    degraded: "bg-amber-500",
    offline:  "bg-red-500",
    loading:  "bg-[#2d3d5a]",
  };
  const cls = colors[level] ?? colors.loading;
  const glow = level === "online" ? "shadow-[0_0_4px_#10b981]" : "";
  return (
    <span className={`inline-block w-1.5 h-1.5 rounded-full ${cls} ${glow}`} />
  );
}

export default function Navbar() {
  const pathname  = usePathname();
  const safePath  = typeof pathname === "string" ? pathname : "";
  const pageLabel = ROUTE_LABELS[safePath] ?? "TradeAI";

  const [status, setStatus] = useState<SystemStatus>({ backend: "loading", lastSeen: null });
  const [now,    setNow]    = useState<string>("");

  useEffect(() => {
    const tick = () => {
      try {
        setNow(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
      } catch {
        setNow("");
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const check = async () => {
      try {
        const r = await fetch("/api/v1/system/health", { signal: AbortSignal.timeout(3000) });
        setStatus({
          backend:  r.ok ? "online" : "degraded",
          lastSeen: new Date().toLocaleTimeString("pt-BR"),
        });
      } catch {
        setStatus(s => ({ ...s, backend: "offline" }));
      }
    };
    check();
    const id = setInterval(check, 15_000);
    return () => clearInterval(id);
  }, []);

  const level = status?.backend ?? "loading";
  const label =
    level === "online"   ? "Backend Online"   :
    level === "degraded" ? "Backend Degraded" :
    level === "loading"  ? "Verificando..."   :
    "Backend Offline";

  return (
    <header
      className="sticky top-0 z-30 flex items-center px-5 h-14 shrink-0"
      style={{ background: "rgba(8,12,20,0.92)", backdropFilter: "blur(12px)", borderBottom: "1px solid #141c2e" }}
    >
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-sm font-semibold text-white truncate">{pageLabel}</span>
        <span className="hidden md:block text-[#1e3050] text-sm">·</span>
        <span className="hidden md:block text-xs text-[#2d4060]">TradeAI Quantitative Platform</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <StatusDot level={level} />
          <span className="text-[11px] text-[#4a6080] hidden sm:block">{label}</span>
        </div>
        <div className="w-px h-4 bg-[#141c2e]" />
        <span
          className="text-[10px] font-mono px-2 py-0.5 rounded border"
          style={{ color: "#3d5a80", borderColor: "#141c2e", background: "#0d1525" }}
        >
          v12.0.0
        </span>
        <span className="text-[11px] font-mono text-[#2d4060] hidden md:block w-[68px] text-right">
          {now}
        </span>
      </div>
    </header>
  );
}
