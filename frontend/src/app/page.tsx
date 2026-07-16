"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  getPaperStats,
  getWorkerAccount,
  getScalperAccount,
  getAgentsStatus,
  getFearGreed,
  getMarketStats,
} from "@/lib/api";
import type {
  PaperStatsResponse,
  WorkerAccountResponse,
  ScalperAccountResponse,
  AgentsStatusResponse,
  FearGreedData,
  MarketStatsResponse,
} from "@/types/index";

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

// ── Agent balance type ────────────────────────────────────────────────────────

interface AgentBalance {
  name:      string;
  balance:   number;
  initial:   number;
  pnl:       number;
  pnlPct:    number;
  color:     string;
  icon:      string;
  href:      string;
  status?:   string;  // "online" | "offline" | "idle"
  trades?:   number;
  wins?:     number;
  losses?:   number;
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

function AgentCard({ agent }: { agent: AgentBalance }) {
  const pnlPositive = agent.pnl >= 0;
  const pnlColor = pnlPositive ? "text-emerald-400" : "text-red-400";
  const hasData = agent.balance !== agent.initial || agent.trades;

  const statusColor = agent.status === "online"
    ? "bg-emerald-900/30 text-emerald-400"
    : agent.status === "idle"
    ? "bg-amber-900/30 text-amber-400"
    : "bg-[#141c2e] text-[#4a6080]";
  const statusLabel = agent.status === "online" ? "online" : agent.status === "idle" ? "idle" : "offline";
  const dotColor = agent.status === "online"
    ? "bg-emerald-500 shadow-[0_0_6px_#10b981]"
    : agent.status === "idle"
    ? "bg-amber-500"
    : "bg-[#2d4060]";

  return (
    <Link href={agent.href} className="block">
      <div className="rounded-xl p-4 transition-all hover:scale-[1.02] hover:border-opacity-60"
        style={{ background: "#0d1220", border: `1px solid ${agent.color}25` }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm"
              style={{ background: `${agent.color}20`, border: `1px solid ${agent.color}40`, color: agent.color }}>
              {agent.icon}
            </div>
            <span className="text-xs font-bold text-white">{agent.name}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
            <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${statusColor}`}>
              {statusLabel}
            </span>
          </div>
        </div>

        {/* Balance */}
        <div className="mb-2">
          <span className="text-[9px] text-[#2d4060] uppercase tracking-wider">Saldo</span>
          <div className="text-base font-bold font-mono text-white">
            ${agent.balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        {/* PnL */}
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[9px] text-[#2d4060] uppercase tracking-wider">PnL</span>
            <div className={`text-sm font-bold font-mono ${pnlColor}`}>
              {pnlPositive ? "+" : ""}{agent.pnlPct.toFixed(2)}%
            </div>
          </div>
          {agent.trades != null && (
            <div className="text-right">
              <span className="text-[9px] text-[#2d4060] uppercase tracking-wider">Trades</span>
              <div className="text-sm font-bold text-white">{agent.trades}</div>
            </div>
          )}
          {agent.wins != null && (
            <div className="text-right">
              <span className="text-[9px] text-[#2d4060] uppercase tracking-wider">W/L</span>
              <div className="text-sm font-bold">
                <span className="text-emerald-400">{agent.wins}</span>
                <span className="text-[#2d4060]">/</span>
                <span className="text-red-400">{agent.losses}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </Link>
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

  // Agent accounts
  const [worker, setWorker]   = useState<WorkerAccountResponse | null>(null);
  const [scalper, setScalper] = useState<ScalperAccountResponse | null>(null);
  const [paper, setPaper]     = useState<PaperStatsResponse | null>(null);
  const [agentsStatus, setAgentsStatus] = useState<AgentsStatusResponse | null>(null);

  // Market data
  const [btc, setBtc]             = useState<MarketStatsResponse | null>(null);
  const [fearGreed, setFearGreed] = useState<FearGreedData | null>(null);

  useEffect(() => {
    // ── Agent accounts ──
    getPaperStats().then(d => { if (d) { setStats(d); setPaper(d); } }).catch(() => {});
    getWorkerAccount().then(d => setWorker(d)).catch(() => {});
    getScalperAccount().then(d => setScalper(d)).catch(() => {});
    getAgentsStatus().then(d => setAgentsStatus(d)).catch(() => {});

    // ── Market data ──
    getMarketStats("BTCUSDT").then(d => setBtc(d)).catch(() => {});
    getFearGreed().then(d => setFearGreed(d)).catch(() => {});

    // ── Regime ──
    const regimeUrl = "/api/v1/analytics/regime/BTCUSDT?timeframe=1h&history_limit=1";
    fetch(regimeUrl)
      .then(r => r.json())
      .then((d: unknown) => {
        const body = d as RegimeHistoryResponse;
        if (body?.current) setRegime(body.current);
      })
      .catch(() => {});

    // ── Sinais de hoje ──
    const today = new Date().toISOString().split("T")[0] ?? "";
    const signalsUrl = "/api/v1/analytics/signals?limit=500";
    fetch(signalsUrl)
      .then(r => r.json())
      .then((d: unknown) => {
        const arr = safeArray<SignalRow>(Array.isArray(d) ? d : ((d as { signals?: unknown[] })?.signals ?? []));
        const count = arr.filter(s => safeString(s?.created_at ?? s?.timestamp).startsWith(today)).length;
        setSignalsToday(count);
      })
      .catch(() => {});

    // ── System health ──
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

    // Refresh agent status every 15s
    const idAgents = setInterval(() => {
      getAgentsStatus().then(d => setAgentsStatus(d)).catch(() => {});
    }, 15_000);

    return () => { clearInterval(id); clearInterval(idAgents); };
  }, []);

  // ── Build agent balances ──────────────────────────────────────────────────
  const agentStatusMap = (agentsStatus?.agents ?? []).reduce(
    (acc, a) => ({ ...acc, [a.name]: a.status }), {} as Record<string, string>,
  );

  const agents: AgentBalance[] = [
    {
      name: "Worker",
      balance: worker?.balance ?? 10000,
      initial: worker?.initial_balance ?? 10000,
      pnl: worker?.total_pnl ?? 0,
      pnlPct: worker ? ((worker.balance / worker.initial_balance) - 1) * 100 : 0,
      color: "#7c3aed",
      icon: "\u2699",
      href: "/worker",
      status: agentStatusMap["Worker"] ?? "offline",
      trades: worker?.total_trades,
      wins: worker?.winning_trades,
      losses: worker?.losing_trades,
    },
    {
      name: "Scalper",
      balance: scalper?.balance ?? 10000,
      initial: scalper?.initial_balance ?? 10000,
      pnl: scalper?.total_pnl ?? 0,
      pnlPct: scalper ? ((scalper.balance / scalper.initial_balance) - 1) * 100 : 0,
      color: "#f59e0b",
      icon: "\u26a1",
      href: "/scalper",
      status: agentStatusMap["Scalper"] ?? "offline",
    },
{
      name: "Paper",
      balance: paper?.balance ?? 200,
      initial: paper?.initial_balance ?? 200,
      pnl: paper?.total_pnl ?? 0,
      pnlPct: paper ? ((paper.balance / paper.initial_balance) - 1) * 100 : 0,
      color: "#2563eb",
      icon: "◆",
      href: "/paper-trading",
      status: agentStatusMap["Paper"] ?? "offline",
      trades: paper?.closed_trades,
      wins: paper ? Math.round(paper.closed_trades * paper.win_rate / 100) : undefined,
      losses: paper ? paper.closed_trades - Math.round(paper.closed_trades * paper.win_rate / 100) : undefined,
    },
  ];

  const totalBalance = agents.reduce((s, a) => s + a.balance, 0);
  const totalInitial = agents.reduce((s, a) => s + a.initial, 0);
  const totalPnl = totalBalance - totalInitial;
  const totalPnlPct = totalInitial > 0 ? ((totalBalance / totalInitial) - 1) * 100 : 0;

  // ── Safe derived display values ───────────────────────────────────────────
  const hasStats = stats != null;
  const openTrades  = hasStats ? String(safeNumber(stats?.open_trades)) : "\u2014";
  const winRateNum  = safeNumber(stats?.win_rate);
  const pfNum       = safeNumber(stats?.profit_factor);
  const totalPnlPaper = safeNumber(stats?.total_pnl);
  const closedNum   = safeNumber(stats?.closed_trades);

  const balance   = hasStats
    ? `$${safeNumber(stats?.current_balance).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "\u2014";
  const winRate   = hasStats ? `${winRateNum.toFixed(1)}%` : "\u2014";
  const pf        = hasStats ? (pfNum >= 999 ? "\u221e" : pfNum.toFixed(2)) : "\u2014";
  const totalPnlPaperStr  = hasStats
    ? `${totalPnlPaper >= 0 ? "+" : ""}$${Math.abs(totalPnlPaper).toFixed(2)}`
    : "\u2014";
  const sigLabel  = signalsToday != null ? String(signalsToday) : "\u2014";

  const regimeLabel = safeString(regime?.regime, "\u2014");
  const regimeConf  = safeNumber(regime?.confidence, 0);

  const pnlColor = !hasStats ? "text-white" : totalPnlPaper >= 0 ? "text-emerald-400" : "text-red-400";
  const wrColor  = !hasStats ? "text-white" : winRateNum  >= 50 ? "text-emerald-400" : "text-red-400";
  const pfColor  = !hasStats ? "text-white" : pfNum       >= 1  ? "text-emerald-400" : "text-red-400";
  const regColor =
    regimeLabel === "BULL"            ? "text-emerald-400" :
    regimeLabel === "BEAR"            ? "text-red-400"     :
    regimeLabel === "HIGH_VOLATILITY" ? "text-amber-400"   : "text-[#8aa4c8]";

  const bkLevel = health?.backend ?? "loading";

  // BTC display
  const btcPrice = btc?.price;
  const btcChange = btc?.change_24h;
  const btcPriceStr = btcPrice != null
    ? `$${btcPrice.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    : "\u2014";
  const btcChangeStr = btcChange != null
    ? `${btcChange >= 0 ? "+" : ""}${btcChange.toFixed(2)}%`
    : "";
  const btcChangeColor = btcChange != null
    ? btcChange >= 0 ? "text-emerald-400" : "text-red-400"
    : "text-[#4a6080]";

  // Fear & Greed
  const fgValue = fearGreed?.value;
  const fgLabel = fearGreed?.classification ?? "\u2014";
  const fgColor = fgValue != null
    ? fgValue < 25 ? "text-red-400" :
      fgValue < 45 ? "text-amber-400" :
      fgValue < 55 ? "text-[#8aa4c8]" :
      fgValue < 75 ? "text-emerald-300" : "text-emerald-400"
    : "text-[#4a6080]";

  // Total portfolio
  const totalPnlColor = totalPnl >= 0 ? "text-emerald-400" : "text-red-400";

  // render

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
            4 agentes ativos · Deterministico · Multi-Strategy
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* BTC Price */}
          {btcPrice != null && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
              style={{ background: "#0d1220", border: "1px solid #141c2e" }}>
              <span className="text-[10px] text-[#4a6080] font-bold">BTC</span>
              <span className="text-sm font-bold font-mono text-white">{btcPriceStr}</span>
              <span className={`text-[10px] font-bold ${btcChangeColor}`}>{btcChangeStr}</span>
            </div>
          )}
          {/* System status */}
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
      </div>

      {/* Portfolio Overview — All Agents */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[9px] text-[#1e3050] uppercase tracking-widest font-semibold">
            Portfolio — Todos os Agentes
          </div>
          <div className="flex items-center gap-4 text-[10px]">
            <span className="text-[#2d4060]">
              Total: <span className="font-bold text-white">${totalBalance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </span>
            <span className="text-[#2d4060]">
              PnL: <span className={`font-bold ${totalPnlColor}`}>
                {totalPnl >= 0 ? "+" : ""}{totalPnlPct.toFixed(2)}%
              </span>
            </span>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {agents.map(a => <AgentCard key={a.name} agent={a} />)}
        </div>
      </section>

      {/* Quick Metrics — Market + Paper */}
      <section>
        <div className="text-[9px] text-[#1e3050] uppercase tracking-widest mb-3 font-semibold">
          Metricas Rapidas
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          <MetricCard label="Fear & Greed" value={fgValue != null ? String(fgValue) : "\u2014"} sub={fgLabel} color={fgColor} />
          <MetricCard label="Regime BTC/1h"  value={regimeLabel} sub={regime != null ? `${regimeConf.toFixed(0)}% conf.` : undefined} color={regColor} />
          <MetricCard label="Sinais Hoje"     value={sigLabel}    sub="BTC / ETH / SOL" />
          <MetricCard label="Win Rate"        value={winRate}     sub={`${closedNum} fechados`}                          color={wrColor}  />
          <MetricCard label="Profit Factor"  value={pf}                                                                 color={pfColor}  />
          <MetricCard label="PnL Paper"       value={totalPnlPaperStr}                                                          color={pnlColor} />
          <MetricCard label="Trades Abertos" value={openTrades}  sub="Posicoes ativas"                                               />
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
                ["Frontend", "Next.js 14 + Tailwind"],
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
          TradeAI v12.0.0 · 3 Agents · Multi-Strategy · Deterministico
        </p>
      </footer>

    </div>
  );
}
