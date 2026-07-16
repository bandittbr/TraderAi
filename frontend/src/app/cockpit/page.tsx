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

        {/* ── Main Layout: Chart + AI Insights ───────────────────────────── */}
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-4">
          <TradingChart />
          <AIInsights />
        </div>

        {/* ── Market Heatmap ──────────────────────────────────────────────── */}
        <MarketHeatmap />

        {/* ── Performance Metrics ─────────────────────────────────────────── */}
        <PerformanceMetrics />

        {/* ── Portfolio Table ──────────────────────────────────────────────── */}
        <PortfolioTable />

        {/* ── Agent Fleet ──────────────────────────────────────────────────── */}
        <AgentFleet />

        {/* ── Ranking + Sentiment ─────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_1.5fr] gap-4">
          <RankingAgents />
          <SentimentGauge />
        </div>

        {/* ── Performance Calendar ─────────────────────────────────────────── */}
        <PerformanceCalendar />

        {/* ── Footer ─────────────────────────────────────────────────────── */}
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
      </div>
    </div>
  );
}