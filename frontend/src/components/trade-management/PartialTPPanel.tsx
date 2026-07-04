"use client";

import { useEffect, useState } from "react";

interface LifecycleEvent {
  id: number;
  trade_id: number;
  event_type: string;
  price: number | null;
  quantity: number | null;
  pnl: number | null;
  notes: string | null;
  created_at: string;
}

interface Stats {
  partial_tp_count:    number;
  partial_tp_rate_pct: number;
  take_profit_count:   number;
  avg_pnl_take_profit: number | null;
}

export default function PartialTPPanel() {
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [stats, setStats]   = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [rE, rS] = await Promise.all([
          fetch("/api/v1/trade-management/events?limit=100"),
          fetch("/api/v1/trade-management/stats"),
        ]);
        if (rE.ok) {
          const all: LifecycleEvent[] = await rE.json();
          setEvents(all.filter((e) => e.event_type === "PARTIAL_EXIT"));
        }
        if (rS.ok) setStats(await rS.json());
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

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4">
      <h2 className="text-sm font-semibold text-white mb-3">Partial Take Profit (TP1/TP2)</h2>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-emerald-400">{stats?.partial_tp_count ?? 0}</div>
          <div className="text-[10px] text-[#6b7280]">TP1 Ativados</div>
        </div>
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-white">{stats?.take_profit_count ?? 0}</div>
          <div className="text-[10px] text-[#6b7280]">TP2 Full Close</div>
        </div>
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-white">
            {stats?.avg_pnl_take_profit != null
              ? `$${(stats.avg_pnl_take_profit ?? 0).toFixed(2)}`
              : "—"}
          </div>
          <div className="text-[10px] text-[#6b7280]">PnL Médio TP</div>
        </div>
      </div>

      {/* Events */}
      {events.length === 0 ? (
        <p className="text-xs text-[#6b7280]">Nenhum TP1 parcial ainda.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {events.map((e) => (
            <div key={e.id} className="bg-[#0d1117] border border-[#1f2937] rounded-lg px-3 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-900/40 text-emerald-400 border border-emerald-800/40">
                    PARTIAL EXIT
                  </span>
                  <span className="text-xs text-white">Trade #{e.trade_id}</span>
                </div>
                <span
                  className={`text-xs font-semibold ${(e.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}
                >
                  {(e.pnl ?? 0) >= 0 ? "+" : ""}${(e.pnl ?? 0).toFixed(4)}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-[#9ca3af]">
                {e.price != null && <span>@ ${(e.price ?? 0).toFixed(2)}</span>}
                {e.quantity != null && <span className="ml-2">qty={e.quantity.toFixed(6)}</span>}
                {e.notes && <span className="ml-2 text-[#6b7280]">{e.notes}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
