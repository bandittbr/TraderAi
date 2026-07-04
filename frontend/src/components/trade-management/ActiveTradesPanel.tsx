"use client";

import { useEffect, useState } from "react";

interface ActiveTrade {
  id: number;
  symbol: string;
  side: string;
  entry_price: number;
  quantity: number;
  hours_open: number;
  max_hours: number;
  time_stop_in_hours: number;
  break_even_activated: boolean;
  trailing_stop_active: boolean;
  trailing_stop_price: number | null;
  tp1_hit: boolean;
  remaining_quantity: number | null;
}

export default function ActiveTradesPanel() {
  const [trades, setTrades] = useState<ActiveTrade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/v1/trade-management/active");
        if (r.ok) setTrades(await r.json());
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

  const sideColor = (s: string) =>
    s === "LONG" ? "text-green-400" : "text-red-400";

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4">
      <h2 className="text-sm font-semibold text-white mb-3">
        Trades Abertos — Gerenciamento Fase 12
        <span className="ml-2 text-xs text-[#6b7280]">({trades.length})</span>
      </h2>

      {trades.length === 0 ? (
        <p className="text-xs text-[#6b7280]">Nenhum trade aberto.</p>
      ) : (
        <div className="space-y-3">
          {trades.map((t) => {
            const pctTime = Math.min(100, (t.hours_open / t.max_hours) * 100);
            return (
              <div key={t.id} className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-3 space-y-2">
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{t.symbol}</span>
                    <span className={`text-xs font-bold ${sideColor(t.side)}`}>{t.side}</span>
                  </div>
                  <span className="text-xs text-[#9ca3af]">
                    {t.hours_open.toFixed(1)}h aberto
                  </span>
                </div>

                {/* Entry */}
                <div className="flex gap-4 text-xs text-[#9ca3af]">
                  <span>Entrada: <span className="text-white">${(t.entry_price ?? 0).toFixed(2)}</span></span>
                  <span>Qty: <span className="text-white">{(t.quantity ?? 0).toFixed(6)}</span></span>
                </div>

                {/* Time bar */}
                <div>
                  <div className="flex justify-between text-[10px] text-[#6b7280] mb-1">
                    <span>Time Stop: {t.time_stop_in_hours.toFixed(1)}h restantes</span>
                    <span>{pctTime.toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${pctTime > 80 ? "bg-red-500" : pctTime > 50 ? "bg-amber-500" : "bg-green-500"}`}
                      style={{ width: `${pctTime}%` }}
                    />
                  </div>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap gap-1.5">
                  {t.break_even_activated && (
                    <span className="px-1.5 py-0.5 bg-blue-900/40 text-blue-400 text-[10px] rounded border border-blue-800/40">
                      BE ATIVO
                    </span>
                  )}
                  {t.trailing_stop_active && (
                    <span className="px-1.5 py-0.5 bg-purple-900/40 text-purple-400 text-[10px] rounded border border-purple-800/40">
                      TRAILING {t.trailing_stop_price ? `$${(t.trailing_stop_price ?? 0).toFixed(2)}` : ""}
                    </span>
                  )}
                  {t.tp1_hit && (
                    <span className="px-1.5 py-0.5 bg-emerald-900/40 text-emerald-400 text-[10px] rounded border border-emerald-800/40">
                      TP1 HIT · qty={((t.remaining_quantity ?? 0)).toFixed(6)}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
