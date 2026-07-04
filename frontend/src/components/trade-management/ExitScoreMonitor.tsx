"use client";

import { useEffect, useState } from "react";

interface Stats {
  total_closed_trades:    number;
  exit_score_count:       number;
  avg_exit_score:         number | null;
  time_stop_count:        number;
  trailing_stop_count:    number;
  break_even_stop_count:  number;
  stop_loss_count:        number;
  take_profit_count:      number;
  signal_close_count:     number;
  partial_tp_count:       number;
  time_stop_rate_pct:     number;
  trailing_stop_rate_pct: number;
  partial_tp_rate_pct:    number;
  avg_duration_hours:     number;
  avg_pnl_time_stop:      number | null;
  avg_pnl_trailing_stop:  number | null;
  avg_pnl_take_profit:    number | null;
  avg_pnl_stop_loss:      number | null;
}

function ScoreBar({ value }: { value: number }) {
  const color =
    value >= 60 ? "bg-green-500" :
    value >= 40 ? "bg-amber-500" :
    "bg-red-500";
  return (
    <div className="h-2 bg-[#1f2937] rounded-full overflow-hidden">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
    </div>
  );
}

export default function ExitScoreMonitor() {
  const [stats, setStats]   = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/v1/trade-management/stats");
        if (r.ok) setStats(await r.json());
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <div className="text-xs text-[#6b7280] p-4">Carregando...</div>;
  if (!stats)  return <div className="text-xs text-[#6b7280] p-4">Sem dados.</div>;

  const n = stats.total_closed_trades;

  const closeReasons = [
    { label: "Take Profit",     count: stats.take_profit_count,    color: "text-green-400" },
    { label: "Signal Close",    count: stats.signal_close_count,   color: "text-blue-400" },
    { label: "Trailing Stop",   count: stats.trailing_stop_count,  color: "text-purple-400" },
    { label: "Break Even Stop", count: stats.break_even_stop_count,color: "text-blue-300" },
    { label: "Stop Loss",       count: stats.stop_loss_count,      color: "text-red-400" },
    { label: "Time Stop",       count: stats.time_stop_count,      color: "text-amber-400" },
    { label: "Exit Score",      count: stats.exit_score_count,     color: "text-orange-400" },
  ];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4 space-y-4">
      <h2 className="text-sm font-semibold text-white">Exit Score Monitor + Estatísticas</h2>

      {/* Exit Score */}
      {stats.avg_exit_score != null && (
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-3">
          <div className="flex justify-between items-center mb-1">
            <span className="text-xs text-[#9ca3af]">Exit Score Médio (fechados)</span>
            <span className={`text-sm font-bold ${stats.avg_exit_score >= 40 ? "text-green-400" : "text-red-400"}`}>
              {(stats.avg_exit_score ?? 0).toFixed(1)} / 100
            </span>
          </div>
          <ScoreBar value={stats.avg_exit_score ?? 0} />
        </div>
      )}

      {/* Overview */}
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-white">{n}</div>
          <div className="text-[10px] text-[#6b7280]">Total Trades</div>
        </div>
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-white">{(stats.avg_duration_hours ?? 0).toFixed(1)}h</div>
          <div className="text-[10px] text-[#6b7280]">Duração Média</div>
        </div>
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-emerald-400">{(stats.partial_tp_rate_pct ?? 0).toFixed(1)}%</div>
          <div className="text-[10px] text-[#6b7280]">Taxa TP1</div>
        </div>
      </div>

      {/* Close reason breakdown */}
      <div>
        <div className="text-xs text-[#6b7280] mb-2">Distribuição de Fechamentos</div>
        <div className="space-y-1.5">
          {closeReasons.map(({ label, count, color }) => {
            const pct = n > 0 ? (count / n) * 100 : 0;
            return (
              <div key={label} className="flex items-center gap-2">
                <div className="w-28 text-[10px] text-[#9ca3af] shrink-0">{label}</div>
                <div className="flex-1 h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${color.replace("text-", "bg-")}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className={`text-[10px] w-8 text-right ${color}`}>{count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* PnL by reason */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: "PnL Médio TP",      val: stats.avg_pnl_take_profit },
          { label: "PnL Médio SL",      val: stats.avg_pnl_stop_loss },
          { label: "PnL Médio Trailing", val: stats.avg_pnl_trailing_stop },
          { label: "PnL Médio TimeStop", val: stats.avg_pnl_time_stop },
        ].map(({ label, val }) => (
          <div key={label} className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2">
            <div className="text-[10px] text-[#6b7280] mb-0.5">{label}</div>
            <div className={`text-xs font-semibold ${val == null ? "text-[#6b7280]" : val >= 0 ? "text-green-400" : "text-red-400"}`}>
              {val == null ? "—" : `${val >= 0 ? "+" : ""}$${(val ?? 0).toFixed(4)}`}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
