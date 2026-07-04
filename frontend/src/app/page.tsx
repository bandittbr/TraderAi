"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPaperStats } from "@/lib/api";
import type { PaperStatsResponse } from "@/types/index";

// ── Defensive helpers ─────────────────────────────────────────────────────────

function safeNumber(v: unknown, fallback = 0): number {
  const n = Number(v);
  return isFinite(n) ? n : fallback;
}

function safeArray<T>(v: unknown): T[] {
  return Array.isArray(v) ? (v as T[]) : [];
}

function safeString(v: unknown, fallback = ""): string {
  return typeof v === "string" ? v : fallback;
}

// ── API types ─────────────────────────────────────────────────────────────────

interface RegimeCurrent {
  regime:     string;
  confidence: number;
}

interface RegimeHistoryResponse {
  current: RegimeCurrent | null;
}

interface SignalRow {
  created_at?: unknown;
  timestamp?:  unknown;
}

type SLevel = "online" | "offline" | "degraded" | "loading";

interface HealthStatus {
  backend:    SLevel;
  database:   SLevel;
  scheduler:  SLevel;
  marketData: SLevel;
}

// ── Module definitions ────────────────────────────────────────────────────────

const MODULES = [
  {
    title: "Dashboard",
    description: "Graficos de preco, indicadores tecnicos, Market Score e Smart Money em tempo real.",
    href: "/dashboard",
    icon: "\u25c8", accent: "#3b82f6", tag: "Live", external: false,
  },
  {
    title: "Paper Trading",
    description: "Simulador de futures com LONG/SHORT, historico de trades e metricas de performance.",
    href: "/paper-trading",
    icon: "\u25ce", accent: "#f59e0b", tag: "Live", external: false,
  },
  {
    title: "Trade Management",
    description: "Time Stop, Break Even, Trailing Stop, Partial TP e Exit Score por posicao aberta.",
    href: "/trade-management",
    icon: "\u25c9", accent: "#06b6d4", tag: "Fase 12", external: false,
  },
  {
    title: "Analytics",
    description: "Win rate, Sharpe Ratio, Profit Factor, analise por regime e historico de sinais.",
    href: "/analytics",
    icon: "\u25b2", accent: "#10b981", tag: "Historico", external: false,
  },
  {
    title: "Alpha Discovery",
    description: "Engine de descoberta de padroes alfa com analise estatistica de setups.",
    href: "/alpha",
    icon: "\u25c6", accent: "#8b5cf6", tag: "Fase 9", external: false,
  },
  {
    title: "Robustness Engine",
    description: "Walk Forward, Monte Carlo e analise de estabilidade estatistica da estrategia.",
    href: "/robustness",
    icon: "\u25c7", accent: "#ec4899", tag: "Fase 10", external: false,
  },
  {
    title: "Strategy Lab",
    description: "Strategy Evolution Engine com geracao, avaliacao e ranking de estrategias.",
    href: "/strategies",
    icon: "\u2b21", accent: "#f97316", tag: "Fase 11", external: false,
  },
  {
    title: "API Docs",
    description: "Documentacao Swagger interativa com todos os endpoints do backend FastAPI.",
    href: "http://localhost:8000/docs",
    icon: "\u229e", accent: "#6b7280", tag: "Swagger", external: true,
  },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusPill({ label, status }: { label: string; status: SLevel }) {
  const map: Record<SLevel, { dot: string; text: string; badge: string }> = {
    online:   { dot: "bg-emerald-500 shadow-[0_0_6px_#10b981]", text: "Online",   badge: "text-emerald-400" },
    degraded: { dot: "bg-amber-500",                             text: "Degraded", badge: "text-amber-400"   },
    offline:  { dot: "bg-red-500",                               text: "Offline",  badge: "text-red-400"     },
    loading:  { dot: "bg-[#1e3050] animate-pulse",               text: "...",      badge: "text-[#3d5a80]"   },
  };
  const { dot, text, badge } = map[status] ?? map.loading;
  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-lg"
      style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
      <span className="text-xs text-[#4a6080]">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <span className={`text-xs font-medium ${badge}`}>{text}</span>
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub, color = "text-white" }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl px-4 py-3 flex flex-col gap-1"
      style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
      <span className="text-[10px] text-[#2d4060] uppercase tracking-widest">{label}</span>
      <span className={`text-lg font-bold leading-none font-mono ${color}`}>{value}</span>
      {sub != null && <span className="text-[10px] text-[#2d4060]">{sub}</span>}
    </div>
  );
}

function ModuleCard({ title, description, href, icon, accent, tag, external }: (typeof MODULES)[0]) {
  const inner = (
    <div className="group relative flex flex-col h-full rounded-xl p-5 transition-all"
      style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
      <div className="flex items-start justify-between mb-3">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center text-lg shrink-0"
          style={{ background: `${accent}18`, border: `1px solid ${accent}30`, color: accent }}>
          {icon}
        </div>
        <span className="text-[9px] font-semibold px-2 py-0.5 rounded-full tracking-widest"
          style={{ background: `${accent}18`, color: accent, border: `1px solid ${accent}25` }}>
          {tag}
        </span>
      </div>
      <div className="flex-1">
        <h3 className="text-sm font-semibold text-white mb-1.5 group-hover:text-blue-300 transition-colors">{title}</h3>
        <p className="text-xs leading-relaxed" style={{ color: "#3d5a80" }}>{description}</p>
      </div>
      <div className="mt-4 flex items-center gap-1.5 text-xs font-medium" style={{ color: accent }}>
        <span>Acessar</span>
        <span className="group-hover:translate-x-0.5 transition-transform">{external ? "\u2197" : "\u2192"}</span>
      </div>
      <div className="absolute inset-x-0 bottom-0 h-0.5 rounded-b-xl opacity-0 group-hover:opacity-100 transition-opacity"
        style={{ background: accent }} />
    </div>
  );
  if (external) {
    return <a href={href} target="_blank" rel="noopener noreferrer" className="block h-full">{inner}</a>;
  }
  return <Link href={href} className="block h-full">{inner}</Link>;
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ControlCenter() {
  const [stats,        setStats]        = useState<PaperStatsResponse | null>(null);
  const [regime,       setRegime]       = useState<RegimeCurrent | null>(null);
  const [health,       setHealth]       = useState<HealthStatus>({
    backend: "loading", database: "loading", scheduler: "loading", marketData: "loading",
  });
  const [signalsToday, setSignalsToday] = useState<number | null>(null);

  useEffect(() => {
    // ── Paper Trading stats — usa getPaperStats() => GET /api/v1/paper/stats ──
    console.log("[ControlCenter] Fetching: /api/v1/paper/stats via getPaperStats()");
    getPaperStats()
      .then(data => {
        console.log("[ControlCenter] /paper/stats payload:", data);
        if (data) setStats(data);
      })
      .catch(err => console.error("[ControlCenter] /paper/stats error:", err));

    // ── Regime atual — GET /api/v1/analytics/regime/BTCUSDT ──────────────────
    const regimeUrl = "/api/v1/analytics/regime/BTCUSDT?timeframe=1h&history_limit=1";
    console.log("[ControlCenter] Fetching:", regimeUrl);
    fetch(regimeUrl)
      .then(r => r.json())
      .then((d: unknown) => {
        console.log("[ControlCenter] /analytics/regime payload:", d);
        const body = d as RegimeHistoryResponse;
        if (body?.current) setRegime(body.current);
      })
      .catch(err => console.error("[ControlCenter] /analytics/regime error:", err));

    // ── Sinais de hoje — GET /api/v1/analytics/signals ───────────────────────
    const today = new Date().toISOString().split("T")[0] ?? "";
    const signalsUrl = "/api/v1/analytics/signals?limit=500";
    console.log("[ControlCenter] Fetching:", signalsUrl);
    fetch(signalsUrl)
      .then(r => r.json())
      .then((d: unknown) => {
        console.log("[ControlCenter] /analytics/signals payload (first item):", Array.isArray(d) ? d[0] : d);
        const arr = safeArray<SignalRow>(Array.isArray(d) ? d : ((d as { signals?: unknown[] })?.signals ?? []));
        const count = arr.filter(s => safeString(s?.created_at ?? s?.timestamp).startsWith(today)).length;
        setSignalsToday(count);
      })
      .catch(err => console.error("[ControlCenter] /analytics/signals error:", err));

    // ── System health ─────────────────────────────────────────────────────────
    const checkHealth = async () => {
      let bk = false, db = false, sc = false, mkt = false;
      try {
        const r = await fetch("/api/v1/system/health", { signal: AbortSignal.timeout(3000) });
        if (r.ok) {
          bk = true;
          const body = await r.json().catch(() => ({})) as Record<string, unknown>;
          db = body?.database !== "error";
          sc = body?.scheduler !== false;
        }
      } catch { /* offline */ }
      try {
        const r2 = await fetch("/api/v1/market/stats?symbol=BTCUSDT", { signal: AbortSignal.timeout(3000) });
        mkt = r2.ok;
        if (!sc && bk) sc = r2.ok;
      } catch { /* offline */ }
      setHealth({
        backend:    bk  ? "online" : "offline",
        database:   db  ? "online" : (bk ? "degraded" : "offline"),
        scheduler:  sc  ? "online" : (bk ? "degraded" : "offline"),
        marketData: mkt ? "online" : "offline",
      });
    };
    checkHealth();
    const id = setInterval(checkHealth, 20_000);
    return () => clearInterval(id);
  }, []);

  // ── Safe derived display values ───────────────────────────────────────────
  const hasStats = stats != null;
  const balanceNum  = safeNumber(stats?.current_balance);
  const openTrades  = hasStats ? String(safeNumber(stats?.open_trades)) : "\u2014";
  const winRateNum  = safeNumber(stats?.win_rate);
  const pfNum       = safeNumber(stats?.profit_factor);
  const totalPnlNum = safeNumber(stats?.total_pnl);
  const closedNum   = safeNumber(stats?.closed_trades);

  const balance   = hasStats
    ? `$${balanceNum.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "\u2014";
  const winRate   = hasStats ? `${winRateNum.toFixed(1)}%` : "\u2014";
  const pf        = hasStats ? (pfNum >= 999 ? "\u221e" : pfNum.toFixed(2)) : "\u2014";
  const totalPnl  = hasStats
    ? `${totalPnlNum >= 0 ? "+" : ""}$${Math.abs(totalPnlNum).toFixed(2)}`
    : "\u2014";
  const sigLabel  = signalsToday != null ? String(signalsToday) : "\u2014";

  const regimeLabel = safeString(regime?.regime, "\u2014");
  const regimeConf  = safeNumber(regime?.confidence, 0);

  const pnlColor = !hasStats ? "text-white" : totalPnlNum >= 0 ? "text-emerald-400" : "text-red-400";
  const wrColor  = !hasStats ? "text-white" : winRateNum  >= 50 ? "text-emerald-400" : "text-red-400";
  const pfColor  = !hasStats ? "text-white" : pfNum       >= 1  ? "text-emerald-400" : "text-red-400";
  const regColor =
    regimeLabel === "BULL"            ? "text-emerald-400" :
    regimeLabel === "BEAR"            ? "text-red-400"     :
    regimeLabel === "HIGH_VOLATILITY" ? "text-amber-400"   : "text-[#8aa4c8]";

  const bkLevel = health?.backend ?? "loading";

  console.log("[ControlCenter] Render — stats:", stats, "regime:", regime, "signalsToday:", signalsToday);

  return (
    <div className="px-6 py-6 max-w-[1400px] mx-auto space-y-8">

      {/* Hero */}
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-[10px] tracking-widest text-[#2d4060] uppercase mb-1">
            Quantitative Trading Platform
          </div>
          <h1 className="text-2xl font-bold text-white leading-none">Control Center</h1>
          <p className="text-xs text-[#2d4060] mt-1.5">
            Fase 12.5 · 12 modulos ativos · Determinístico · Sem IA generativa
          </p>
        </div>
        <div
          className="inline-flex items-center gap-1.5 text-[10px] px-3 py-1 rounded-full"
          style={{
            background:  bkLevel === "online" ? "#052e16" : "#2d0a0a",
            border:      "1px solid",
            borderColor: bkLevel === "online" ? "#14532d" : "#7f1d1d",
          }}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${bkLevel === "online" ? "bg-emerald-500" : "bg-red-500"}`} />
          <span className={bkLevel === "online" ? "text-emerald-400" : "text-red-400"}>
            {bkLevel === "online" ? "Sistema Operacional" : bkLevel === "loading" ? "Verificando..." : "Backend Offline"}
          </span>
        </div>
      </div>

      {/* Quick Metrics */}
      <section>
        <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-3 font-semibold">
          Metricas Rapidas — Paper Trading
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <MetricCard label="Saldo Virtual"  value={balance}     sub="Paper Account"                                    color={pnlColor} />
          <MetricCard label="Trades Abertos" value={openTrades}  sub="Posicoes ativas"                                               />
          <MetricCard label="Win Rate"        value={winRate}     sub={`${closedNum} fechados`}                          color={wrColor}  />
          <MetricCard label="Profit Factor"  value={pf}                                                                 color={pfColor}  />
          <MetricCard label="PnL Total"       value={totalPnl}                                                          color={pnlColor} />
          <MetricCard label="Sinais Hoje"     value={sigLabel}    sub="BTC / ETH / SOL"                                               />
          <MetricCard label="Regime BTC/1h"  value={regimeLabel} sub={regime != null ? `${regimeConf.toFixed(0)}% conf.` : undefined} color={regColor} />
        </div>
      </section>

      {/* Health + Modules */}
      <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr] gap-6">

        {/* System Health */}
        <section>
          <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-3 font-semibold">System Health</div>
          <div className="space-y-2">
            <StatusPill label="Backend API" status={health?.backend    ?? "loading"} />
            <StatusPill label="Database"    status={health?.database   ?? "loading"} />
            <StatusPill label="Scheduler"   status={health?.scheduler  ?? "loading"} />
            <StatusPill label="Market Data" status={health?.marketData ?? "loading"} />
          </div>
          <div className="mt-4 rounded-xl p-4" style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
            <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-2 font-semibold">Stack</div>
            <div className="space-y-1.5">
              {([
                ["Backend",  "FastAPI + SQLAlchemy"],
                ["DB",       "SQLite + aiosqlite"],
                ["Frontend", "Next.js 15 + Tailwind"],
                ["Dados",    "Binance REST + WS"],
              ] as [string, string][]).map(([k, v]) => (
                <div key={k} className="flex justify-between text-[10px]">
                  <span className="text-[#2d4060]">{k}</span>
                  <span className="text-[#4a6080]">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Module cards */}
        <section>
          <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-3 font-semibold">Modulos da Plataforma</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {safeArray<(typeof MODULES)[0]>(MODULES).map(m => (
              <ModuleCard key={safeString(m?.href, String(Math.random()))} {...m} />
            ))}
          </div>
        </section>

      </div>

      {/* Footer */}
      <footer className="pt-4 border-t text-center" style={{ borderColor: "#141c2e" }}>
        <p className="text-[10px] text-[#1e3050] font-mono">
          TradeAI v12.0.0 · Fase 12.5 UX Layer · Deterministico · Sem IA Generativa · Sem SaaS
        </p>
      </footer>

    </div>
  );
}
