"use client";

import type { PaperStatsResponse } from "@/types";

interface StatItemProps {
  label:    string;
  value:    string;
  sub?:     string;
  color?:   string;
}

function StatItem({ label, value, sub, color }: StatItemProps) {
  return (
    <div className="bg-[#0a0e1a] rounded-lg p-3">
      <p className="text-xs text-[#6b7280] mb-1">{label}</p>
      <p className={`text-lg font-bold ${color ?? "text-[#f9fafb]"}`}>{value}</p>
      {sub && <p className="text-xs text-[#4b5563] mt-0.5">{sub}</p>}
    </div>
  );
}

interface Props {
  stats:   PaperStatsResponse | null;
  loading?: boolean;
}

export function PaperStatsGrid({ stats, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-[#f9fafb] mb-4">Performance</h3>

      {loading || !stats ? (
        <div className="h-32 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {/* Row 1: métricas principais */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatItem
              label="Win Rate"
              value={`${stats.win_rate.toFixed(1)}%`}
              sub={`${stats.closed_trades} fechados`}
              color={stats.win_rate >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
            <StatItem
              label="Profit Factor"
              value={stats.profit_factor === Infinity ? "∞" : stats.profit_factor.toFixed(2)}
              sub="Ganho / Perda"
              color={stats.profit_factor >= 1 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
            <StatItem
              label="Max Drawdown"
              value={`${stats.max_drawdown.toFixed(2)}%`}
              color={stats.max_drawdown > 10 ? "text-[#ef4444]" : "text-[#f59e0b]"}
            />
            <StatItem
              label="PnL Total"
              value={`${stats.total_pnl >= 0 ? "+" : ""}$${stats.total_pnl.toFixed(2)}`}
              sub={`${stats.total_pnl_pct >= 0 ? "+" : ""}${stats.total_pnl_pct.toFixed(2)}%`}
              color={stats.total_pnl >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
          </div>

          {/* Row 2: LONG vs SHORT comparativo */}
          <div className="grid grid-cols-2 gap-3">
            {/* LONG */}
            <div className="bg-[#0a0e1a] rounded-lg p-3 border border-emerald-500/15">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wide">▲ LONG</span>
                <span className="text-[10px] text-[#6b7280]">{stats.long_trades ?? 0} trades</span>
              </div>
              <p className={`text-lg font-bold ${(stats.win_rate_long ?? 0) >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {(stats.win_rate_long ?? 0).toFixed(1)}%
              </p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">Win Rate</p>
            </div>

            {/* SHORT */}
            <div className="bg-[#0a0e1a] rounded-lg p-3 border border-red-500/15">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold text-red-400 uppercase tracking-wide">▼ SHORT</span>
                <span className="text-[10px] text-[#6b7280]">{stats.short_trades ?? 0} trades</span>
              </div>
              <p className={`text-lg font-bold ${(stats.win_rate_short ?? 0) >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {(stats.win_rate_short ?? 0).toFixed(1)}%
              </p>
              <p className="text-[10px] text-[#6b7280] mt-0.5">Win Rate</p>
            </div>
          </div>

          {/* Row 3: métricas secundárias */}
          <div className="grid grid-cols-4 gap-3">
            <StatItem
              label="Ganho Médio"
              value={`$${stats.avg_gain.toFixed(2)}`}
              color="text-[#10b981]"
            />
            <StatItem
              label="Perda Média"
              value={`$${stats.avg_loss.toFixed(2)}`}
              color="text-[#ef4444]"
            />
            <StatItem
              label="Abertos"
              value={String(stats.open_trades)}
              color="text-[#60a5fa]"
            />
            <StatItem
              label="Total"
              value={String(stats.total_trades)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
