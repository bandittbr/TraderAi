"use client";
import { useEffect, useState } from "react";

interface Stats {
  total_trades:    number;
  open_trades:     number;
  win_rate:        number;
  profit_factor:   number;
  total_pnl_usd:   number;
  avg_win_pct:     number;
  avg_loss_pct:    number;
  max_win_pct:     number;
  max_loss_pct:    number;
  avg_duration_min:number;
  by_side:         Record<string, { trades: number; wins: number; losses: number; win_rate: number; profit_factor: number; total_pnl_usd: number }>;
  by_symbol:       Record<string, { trades: number; pnl: number; win_rate: number }>;
  by_reason:       Record<string, number>;
}

function safe(v: unknown, d = 0): number { const n = Number(v); return isFinite(n) ? n : d; }

export default function ScalperStats({ days = 30 }: { days?: number }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const r = await fetch(`/api/v1/scalper/stats?days=${days}`);
        if (r.ok) setStats(await r.json());
      } catch {} finally { setLoading(false); }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [days]);

  if (loading) return <div className="rounded-2xl p-5 animate-pulse" style={{ background: "#0a1020", border: "1px solid #141c2e", height: 200 }} />;

  const pf       = safe(stats?.profit_factor);
  const wr       = safe(stats?.win_rate);
  const pnl      = safe(stats?.total_pnl_usd);
  const pfColor  = pf >= 1.5 ? "text-emerald-400" : pf >= 1 ? "text-amber-400" : "text-red-400";
  const wrColor  = wr >= 55  ? "text-emerald-400" : wr >= 45 ? "text-amber-400" : "text-red-400";

  return (
    <div className="rounded-2xl p-5" style={{ background: "#0a1020", border: "1px solid #141c2e" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Estatísticas — {days}d</h2>
        <span className="text-[10px] text-[#3d5a80]">{safe(stats?.total_trades)} trades</span>
      </div>

      {/* Métricas principais */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        {[
          { label: "Win Rate",      value: `${wr.toFixed(1)}%`,  color: wrColor },
          { label: "Profit Factor", value: pf.toFixed(3),         color: pfColor },
          { label: "PnL Total",     value: `${pnl >= 0 ? "+" : ""}$${pnl.toFixed(2)}`, color: pnl >= 0 ? "text-emerald-400" : "text-red-400" },
          { label: "Duração Média", value: `${safe(stats?.avg_duration_min).toFixed(0)}min`, color: "text-white" },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-xl p-3" style={{ background: "#0d1525", border: "1px solid #141c2e" }}>
            <div className="text-[9px] text-[#3d5a80] uppercase tracking-widest mb-1">{label}</div>
            <div className={`text-lg font-bold font-mono ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Por direção */}
      {stats?.by_side && Object.keys(stats.by_side).length > 0 && (
        <div className="mb-4">
          <div className="text-[10px] text-[#3d5a80] uppercase tracking-widest mb-2">Por Direção</div>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(stats.by_side).map(([side, d]) => (
              <div key={side} className="rounded-xl p-3" style={{ background: "#0d1525", border: "1px solid #141c2e" }}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-xs font-bold ${side === "LONG" ? "text-emerald-400" : "text-red-400"}`}>{side}</span>
                  <span className="text-[10px] text-[#3d5a80]">{d.trades} trades</span>
                </div>
                <div className="text-[11px] text-[#4a6080] space-y-0.5">
                  <div>WR: <span className="text-white">{safe(d.win_rate).toFixed(1)}%</span></div>
                  <div>PF: <span className="text-white">{safe(d.profit_factor).toFixed(3)}</span></div>
                  <div>PnL: <span className={safe(d.total_pnl_usd) >= 0 ? "text-emerald-400" : "text-red-400"}>${safe(d.total_pnl_usd).toFixed(2)}</span></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Por símbolo */}
      {stats?.by_symbol && Object.keys(stats.by_symbol).length > 0 && (
        <div>
          <div className="text-[10px] text-[#3d5a80] uppercase tracking-widest mb-2">Por Ativo</div>
          <div className="space-y-1.5">
            {Object.entries(stats.by_symbol)
              .sort(([,a],[,b]) => b.trades - a.trades)
              .map(([sym, d]) => (
              <div key={sym} className="flex items-center justify-between text-[11px] px-3 py-2 rounded-lg" style={{ background: "#0d1525" }}>
                <span className="text-white font-mono w-20">{sym.replace("USDT","")}</span>
                <span className="text-[#3d5a80]">{d.trades} trades</span>
                <span className="text-[#3d5a80]">WR {safe(d.win_rate).toFixed(0)}%</span>
                <span className={safe(d.pnl) >= 0 ? "text-emerald-400" : "text-red-400"}>
                  {safe(d.pnl) >= 0 ? "+" : ""}${safe(d.pnl).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
