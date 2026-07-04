"use client";

import type { PaperStatsResponse } from "@/types";

interface Props {
  stats:   PaperStatsResponse | null;
  loading?: boolean;
}

function Bar({ value, max = 100, color }: { value: number; max?: number; color: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function StrategyPerformance({ stats, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Strategy Performance</h3>
        <span className="text-xs text-[#4b5563]">Paper Trading</span>
      </div>

      {loading || !stats ? (
        <div className="h-24 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : stats.total_trades === 0 ? (
        <div className="h-24 flex items-center justify-center">
          <p className="text-xs text-[#4b5563]">Aguardando primeiros trades...</p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Win Rate */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-[#6b7280]">Win Rate</span>
              <span className={`text-xs font-semibold ${stats.win_rate >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {stats.win_rate.toFixed(1)}%
              </span>
            </div>
            <Bar
              value={stats.win_rate}
              max={100}
              color={stats.win_rate >= 50 ? "bg-[#10b981]" : "bg-[#ef4444]"}
            />
          </div>

          {/* Profit Factor */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-[#6b7280]">Profit Factor</span>
              <span className={`text-xs font-semibold ${stats.profit_factor >= 1 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {stats.profit_factor === 0 ? "N/A" : stats.profit_factor.toFixed(2)}
              </span>
            </div>
            <Bar
              value={Math.min(stats.profit_factor, 3)}
              max={3}
              color={stats.profit_factor >= 1 ? "bg-[#10b981]" : "bg-[#ef4444]"}
            />
          </div>

          {/* Drawdown */}
          <div>
            <div className="flex justify-between items-center mb-1">
              <span className="text-xs text-[#6b7280]">Max Drawdown</span>
              <span className={`text-xs font-semibold ${stats.max_drawdown > 10 ? "text-[#ef4444]" : "text-[#f59e0b]"}`}>
                {stats.max_drawdown.toFixed(2)}%
              </span>
            </div>
            <Bar
              value={stats.max_drawdown}
              max={30}
              color={stats.max_drawdown > 10 ? "bg-[#ef4444]" : "bg-[#f59e0b]"}
            />
          </div>

          {/* Resumo */}
          <div className="flex justify-between pt-1 border-t border-[#1f2937] text-xs text-[#6b7280]">
            <span>{stats.total_trades} trades · {stats.open_trades} abertos</span>
            <span className={stats.total_pnl >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}>
              {stats.total_pnl >= 0 ? "+" : ""}${stats.total_pnl.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
