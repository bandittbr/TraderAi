"use client";

interface Props {
  stats: {
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
    avg_win_pct: number;
    avg_loss_pct: number;
    max_win_pct: number;
    max_loss_pct: number;
  };
  days: number;
  onDaysChange: (d: number) => void;
}

const PERIODS = [7, 14, 30, 90];

export default function WorkerStats({ stats, days, onDaysChange }: Props) {
  const StatCard = ({ label, value, color = "text-white" }: { label: string; value: string; color?: string }) => (
    <div className="rounded-xl p-4 bg-[#0a1020] border border-[#141c2e]">
      <div className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  );

  const wrColor = stats.win_rate >= 50 ? "text-emerald-400" : "text-red-400";
  const pfColor = stats.profit_factor >= 1.5 ? "text-emerald-400" : stats.profit_factor >= 1 ? "text-amber-400" : "text-red-400";

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-xs font-semibold text-[#4a6080] uppercase tracking-widest">
          Performance ({days}d)
        </h2>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => onDaysChange(p)}
              className={`px-2.5 py-1 rounded text-[10px] font-medium transition-all ${
                days === p
                  ? "bg-blue-600/30 text-blue-300 border border-blue-500/30"
                  : "bg-[#0a1020] text-[#4a6080] border border-[#141c2e] hover:border-[#2a3a5a]"
              }`}
            >
              {p}d
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <StatCard label="Win Rate (Gross)" value={`${stats.win_rate.toFixed(1)}%`} color={wrColor} />
        <StatCard label="Profit Factor" value={stats.profit_factor.toFixed(3)} color={pfColor} />
        <StatCard label="Trades" value={stats.total_trades.toString()} />
        <StatCard label="Open" value={stats.open_trades.toString()} color="text-amber-400" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <StatCard label="Net Win Rate" value={`${stats.net_win_rate.toFixed(1)}%`} color={wrColor} />
        <StatCard label="Net P. Factor" value={stats.net_profit_factor.toFixed(3)} color={pfColor} />
        <StatCard label="Avg Gain" value={`${stats.avg_win_pct.toFixed(2)}%`} color="text-emerald-400" />
        <StatCard label="Avg Loss" value={`${stats.avg_loss_pct.toFixed(2)}%`} color="text-red-400" />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total PnL %" value={`${stats.total_pnl_pct >= 0 ? "+" : ""}${stats.total_pnl_pct.toFixed(2)}%`}
          color={stats.total_pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"} />
        <StatCard label="Net PnL %" value={`${stats.total_net_pnl_pct >= 0 ? "+" : ""}${stats.total_net_pnl_pct.toFixed(2)}%`}
          color={stats.total_net_pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"} />
        <StatCard label="Max Win" value={`${stats.max_win_pct.toFixed(2)}%`} color="text-emerald-400" />
        <StatCard label="Max Loss" value={`${stats.max_loss_pct.toFixed(2)}%`} color="text-red-400" />
      </div>
    </div>
  );
}
