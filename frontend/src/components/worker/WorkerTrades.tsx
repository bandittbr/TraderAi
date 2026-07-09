"use client";

import { useEffect, useState } from "react";

interface WorkerTrade {
  id: number;
  symbol: string;
  trade_side: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  leverage: number;
  pnl_pct: number | null;
  net_pnl_pct: number | null;
  fee_cost_pct: number | null;
  status: string;
  close_reason: string | null;
  confidence: number;
  regime_at_entry: string;
  direction_score: number;
  entry_reason: string | null;
  opened_at: string;
  closed_at: string | null;
  duration_minutes: number | null;
}

export default function WorkerTrades() {
  const [trades, setTrades] = useState<WorkerTrade[]>([]);
  const [filter, setFilter] = useState<string>("ALL");

  useEffect(() => {
    const fetchTrades = async () => {
      try {
        const res = await fetch("/api/v1/worker/trades?limit=50");
        if (res.ok) setTrades(await res.json());
      } catch (e) {
        console.error("[WorkerTrades] fetch error:", e);
      }
    };
    fetchTrades();
    const interval = setInterval(fetchTrades, 20000);
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === "ALL" ? trades : trades.filter((t) => t.status === filter);

  return (
    <div className="rounded-xl bg-[#0a1020] border border-[#141c2e] overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#141c2e]">
        <h2 className="text-xs font-semibold text-[#4a6080] uppercase tracking-widest">
          Histórico de Trades
        </h2>
        <div className="flex gap-1">
          {["ALL", "OPEN", "CLOSED"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all ${
                filter === f
                  ? "bg-blue-600/30 text-blue-300"
                  : "text-[#4a6080] hover:text-white"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-[#141c2e] text-[#4a6080]">
              <th className="text-left px-4 py-2 font-medium">Símbolo</th>
              <th className="text-left px-2 py-2 font-medium">Side</th>
              <th className="text-right px-2 py-2 font-medium">Lev</th>
              <th className="text-right px-2 py-2 font-medium">Entry</th>
              <th className="text-right px-2 py-2 font-medium">Exit</th>
              <th className="text-right px-2 py-2 font-medium">Gross%</th>
              <th className="text-right px-2 py-2 font-medium">Net%</th>
              <th className="text-right px-2 py-2 font-medium">Conf</th>
              <th className="text-left px-2 py-2 font-medium">Regime</th>
              <th className="text-left px-2 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={10} className="text-center py-8 text-[#3b4a6b]">
                  Nenhum trade encontrado
                </td>
              </tr>
            )}
            {filtered.map((t) => {
              const pnl = t.net_pnl_pct ?? t.pnl_pct ?? 0;
              const pnlColor = pnl > 0 ? "text-emerald-400" : pnl < 0 ? "text-red-400" : "text-[#4a6080]";
              return (
                <tr key={t.id} className="border-b border-[#0d1525] hover:bg-[#0d1525]/50">
                  <td className="px-4 py-2 text-white">{t.symbol}</td>
                  <td className={`px-2 py-2 ${t.trade_side === "LONG" ? "text-emerald-400" : "text-red-400"}`}>
                    {t.trade_side}
                  </td>
                  <td className="px-2 py-2 text-right text-[#8aa4c8]">{t.leverage}x</td>
                  <td className="px-2 py-2 text-right text-[#8aa4c8]">{t.entry_price.toFixed(2)}</td>
                  <td className="px-2 py-2 text-right text-[#8aa4c8]">
                    {t.exit_price?.toFixed(2) ?? "—"}
                  </td>
                  <td className={`px-2 py-2 text-right ${pnlColor}`}>
                    {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}%
                  </td>
                  <td className={`px-2 py-2 text-right ${pnlColor}`}>
                    {t.net_pnl_pct != null ? `${t.net_pnl_pct >= 0 ? "+" : ""}${t.net_pnl_pct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-2 py-2 text-right text-[#8aa4c8]">{t.confidence.toFixed(0)}</td>
                  <td className="px-2 py-2 text-[#8aa4c8]">{t.regime_at_entry}</td>
                  <td className="px-2 py-2">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      t.status === "OPEN"
                        ? "bg-amber-900/30 text-amber-400"
                        : t.net_pnl_pct && t.net_pnl_pct > 0
                        ? "bg-emerald-900/30 text-emerald-400"
                        : "bg-red-900/30 text-red-400"
                    }`}>
                      {t.status === "OPEN" ? "OPEN" : (t.close_reason || "CLOSED")}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
