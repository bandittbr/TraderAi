"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import HeaderMetrics from "@/components/Cockpit/HeaderMetrics";
import TradingChart from "@/components/Cockpit/TradingChart";
import AIInsights from "@/components/Cockpit/AIInsights";
import MarketHeatmap from "@/components/Cockpit/MarketHeatmap";
import AgentFleet from "@/components/Cockpit/AgentFleet";
import PerformanceMetrics from "@/components/Cockpit/PerformanceMetrics";
import PortfolioTable from "@/components/Cockpit/PortfolioTable";
import RankingAgents from "@/components/Cockpit/RankingAgents";
import SentimentGauge from "@/components/Cockpit/SentimentGauge";
import PerformanceCalendar from "@/components/Cockpit/PerformanceCalendar";
import {
  getPaperStats,
  getWorkerAccount,
  getScalperAccount,
  getAgentsStatus,
  getFearGreed,
  getMarketStats,
  getAgentsLeaderboard,
} from "@/lib/api";
import type {
  PaperStatsResponse,
  WorkerAccountResponse,
  ScalperAccountResponse,
  AgentsStatusResponse,
  MarketStatsResponse,
  AgentsLeaderboardResponse,
} from "@/types";

type SLevel = "online" | "offline" | "degraded" | "loading";

interface HealthStatus {
  backend: SLevel;
  database: SLevel;
  scheduler: SLevel;
  marketData: SLevel;
}

export default function CockpitPage() {
  // ── States ──────────────────────────────────────────────────────────────
  const [stats, setStats] = useState<PaperStatsResponse | null>(null);
  const [health, setHealth] = useState<HealthStatus>({
    backend: "loading", database: "loading", scheduler: "loading", marketData: "loading",
  });
  const [worker, setWorker] = useState<WorkerAccountResponse | null>(null);
  const [scalper, setScalper] = useState<ScalperAccountResponse | null>(null);
  const [paper, setPaper] = useState<PaperStatsResponse | null>(null);
  const [agentsStatus, setAgentsStatus] = useState<AgentsStatusResponse | null>(null);
  const [btc, setBtc] = useState<MarketStatsResponse | null>(null);
  const [leaderboard, setLeaderboard] = useState<AgentsLeaderboardResponse | null>(null);

  // ── Fetch data ──────────────────────────────────────────────────────────
  useEffect(() => {
    getPaperStats().then(d => { setStats(d); setPaper(d); }).catch(() => {});
    getWorkerAccount().then(d => setWorker(d)).catch(() => {});
    getScalperAccount().then(d => setScalper(d)).catch(() => {});
    getAgentsStatus().then(d => setAgentsStatus(d)).catch(() => {});
    getMarketStats("BTCUSDT").then(d => setBtc(d)).catch(() => {});
    getAgentsLeaderboard().then(d => setLeaderboard(d)).catch(() => {});

    // Health
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
        backend:    bk ? "online" : "offline",
        database:   db ? "online" : (bk ? "degraded" : "offline"),
        scheduler:  sc ? "online" : (bk ? "degraded" : "offline"),
        marketData: mkt ? "online" : "offline",
      });
    };
    checkHealth();
    const id = setInterval(checkHealth, 20_000);
    return () => clearInterval(id);
  }, []);

  // ── Derived values ──────────────────────────────────────────────────────
  const totalCapital = (worker?.balance ?? 10000) + (scalper?.balance ?? 10000) + (paper?.current_balance ?? 200);
  const totalInitial = 10000 + 10000 + 200;
  const totalPnl = totalCapital - totalInitial;
  const winRate = stats?.win_rate ?? 78.6;
  const systemStatus: SLevel = health.backend === "online" ? "online" : "offline";

  const totalTrades = (worker?.total_trades ?? 0) + (leaderboard?.agents?.reduce((s, a) => s + a.total_trades, 0) ?? 0);

  return (
    <div className="min-h-screen" style={{ background: "#050816" }}>
      <div className="max-w-[1600px] mx-auto px-4 py-4 space-y-4">
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <HeaderMetrics
          systemStatus={systemStatus}
          totalCapital={totalCapital}
          totalInitial={totalInitial}
          pnlToday={0}
          pnlMonth={0}
          drawdown={3.21}
          winRate={winRate}
          tradesToday={totalTrades}
          userName="Trader"
          userRole="Fund Manager"
        />

        {/* ── Layout: Sidebar + Main ─────────────────────────────────────── */}
        <div className="flex gap-4">
          {/* Sidebar */}
          <aside className="w-64 flex-shrink-0 space-y-4">
            {/* Navigation */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4 }}
              className="rounded-xl p-3"
              style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
            >
              <nav className="space-y-1">
                {[
                  { label: "Cockpit", icon: "🎛", href: "/cockpit", active: true },
                  { label: "Control Center", icon: "⌘", href: "/", active: false },
                  { label: "Dashboard", icon: "◈", href: "/dashboard", active: false },
                  { label: "Trade Mgmt", icon: "◉", href: "/trade-management", active: false },
                  { label: "Paper", icon: "◎", href: "/paper-trading", active: false },
                  { label: "Scalper", icon: "⚡", href: "/scalper", active: false },
                  { label: "Worker", icon: "⚙", href: "/worker", active: false },
                  { label: "Agents", icon: "⊞", href: "/agents", active: false },
                  { label: "Binance Real", icon: "🏦", href: "/broker", active: false },
                  { label: "Analytics", icon: "▲", href: "/analytics", active: false },
                  { label: "Alpha Discovery", icon: "◆", href: "/alpha", active: false },
                  { label: "Robustness", icon: "◇", href: "/robustness", active: false },
                  { label: "Strategy Lab", icon: "⬡", href: "/strategies", active: false },
                  { label: "Influencer", icon: "★", href: "/influencer", active: false },
                  { label: "API Docs", icon: "⊞", href: "http://localhost:8000/docs", active: false, external: true },
                ].map(item => (
                  <a
                    key={item.href}
                    href={item.href}
                    target={item.external ? "_blank" : undefined}
                    rel={item.external ? "noopener noreferrer" : undefined}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs transition-all ${
                      item.active
                        ? "bg-neon-blue/15 text-neon-blue border border-neon-blue/30"
                        : "text-text-secondary hover:text-text-primary hover:bg-white/2"
                    }`}
                  >
                    <span className="text-sm">{item.icon}</span>
                    <span className={item.active ? "font-semibold" : ""}>{item.label}</span>
                  </a>
                ))}
              </nav>
            </motion.div>

            {/* System Health */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.1 }}
              className="rounded-xl p-3"
              style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
            >
              <div className="text-[9px] text-text-dim uppercase tracking-widest mb-2 font-semibold">SYSTEM HEALTH</div>
              <div className="space-y-2">
                {([
                  ["Backend API", health.backend],
                  ["Database", health.database],
                  ["Scheduler", health.scheduler],
                  ["Market Data", health.marketData],
                ] as [string, SLevel][]).map(([label, status]) => {
                  const config = {
                    online:    { dot: "bg-neon-green shadow-[0_0_8px_#10b981]", text: "Online",   color: "text-neon-green" },
                    degraded:  { dot: "bg-neon-amber shadow-[0_0_8px_#f59e0b]", text: "Degraded", color: "text-neon-amber" },
                    offline:   { dot: "bg-neon-red shadow-[0_0_8px_#ef4444]",   text: "Offline",  color: "text-neon-red" },
                    loading:   { dot: "bg-text-dim",                              text: "Loading", color: "text-text-dim" },
                  }[status];
                  return (
                    <div key={label} className="flex items-center justify-between px-2 py-1.5 rounded-lg" style={{ background: "#050816", border: "1px solid #1a2a4a" }}>
                      <span className="text-[10px] text-text-dim">{label}</span>
                      <div className="flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${config.dot}`} />
                        <span className={`text-[10px] font-medium ${config.color}`}>{config.text}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>

            {/* Quick Stats */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.2 }}
              className="rounded-xl p-3"
              style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
            >
              <div className="text-[9px] text-text-dim uppercase tracking-widest mb-2 font-semibold">QUICK STATS</div>
              <div className="space-y-2">
                {[
                  ["Agentes Ativos", "8", "text-neon-green"],
                  ["Posições Abertas", "5", "text-neon-blue"],
                  ["Ordens Pendentes", "3", "text-neon-amber"],
                  ["Alertas", "0", "text-text-dim"],
                ].map(([label, value, color]) => (
                  <div key={label} className="flex justify-between">
                    <span className="text-[10px] text-text-dim">{label}</span>
                    <span className={`text-[10px] font-bold font-mono ${color}`}>{value}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          </aside>

          {/* Main Area */}
          <main className="flex-1 space-y-4">
            {/* Chart + AI Insights */}
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-4">
              <TradingChart />
              <AIInsights />
            </div>

            {/* Market Heatmap */}
            <MarketHeatmap />

            {/* Performance Metrics */}
            <PerformanceMetrics />

            {/* Portfolio Table */}
            <PortfolioTable />

            {/* Agent Fleet */}
            <AgentFleet />

            {/* Ranking + Sentiment */}
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-4">
              <RankingAgents />
              <SentimentGauge />
            </div>

            {/* Performance Calendar */}
            <PerformanceCalendar />

            {/* Footer */}
            <footer className="pt-3 pb-4 border-t text-center" style={{ borderColor: "#1a2a4a" }}>
              <div className="flex items-center justify-center gap-4 text-[9px] font-mono text-text-dim">
                <span>TRADEAI COCKPIT v14.0.0</span>
                <span className="w-px h-3" style={{ background: "#1a2a4a" }} />
                <span>Quantitative Multi-Agent Platform</span>
                <span className="w-px h-3" style={{ background: "#1a2a4a" }} />
                <span className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${systemStatus === "online" ? "bg-neon-green" : "bg-neon-red"}`} />
                  {systemStatus === "online" ? "Sistema Operacional" : "Offline"}
                </span>
              </div>
            </footer>
          </main>
        </div>
      </div>
    </div>
  );
}