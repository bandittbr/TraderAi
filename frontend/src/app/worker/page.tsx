"use client";

import { useEffect, useState } from "react";
import WorkerAccount from "@/components/worker/WorkerAccount";
import WorkerStats from "@/components/worker/WorkerStats";
import WorkerTrades from "@/components/worker/WorkerTrades";

interface WorkerStatsData {
  period_days: number;
  total_trades: number;
  open_trades: number;
  win_rate: number;
  profit_factor: number;
  total_pnl_usd: number;
  total_pnl_pct: number;
  net_win_rate: number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  avg_duration_min: number;
  balance: number;
  initial_balance: number;
  peak_balance: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  max_win_pct: number;
  max_loss_pct: number;
}

interface WorkerAccountData {
  balance: number;
  initial_balance: number;
  peak_balance: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

export default function WorkerPage() {
  const [account, setAccount] = useState<WorkerAccountData | null>(null);
  const [stats, setStats] = useState<WorkerStatsData | null>(null);
  const [selectedDays, setSelectedDays] = useState(30);

  const fetchData = async (days: number) => {
    try {
      const [accRes, statsRes] = await Promise.all([
        fetch("/api/v1/worker/account"),
        fetch(`/api/v1/worker/stats?days=${days}`),
      ]);
      if (accRes.ok) setAccount(await accRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (e) {
      console.error("[Worker] fetch error:", e);
    }
  };

  useEffect(() => {
    fetchData(selectedDays);
    const interval = setInterval(() => fetchData(selectedDays), 15000);
    return () => clearInterval(interval);
  }, [selectedDays]);

  return (
    <div className="p-4 md:p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Worker Agent</h1>
          <p className="text-sm text-[#4a6080] mt-0.5">
            Agente 24/7 • Multi-timeframe • Alavancagem adaptativa
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-900/40 text-emerald-400 border border-emerald-800/50">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            24/7 Running
          </span>
        </div>
      </div>

      {/* Account */}
      {account && <WorkerAccount account={account} />}

      {/* Stats */}
      {stats && <WorkerStats stats={stats} days={selectedDays} onDaysChange={setSelectedDays} />}

      {/* Trades */}
      <WorkerTrades />
    </div>
  );
}
