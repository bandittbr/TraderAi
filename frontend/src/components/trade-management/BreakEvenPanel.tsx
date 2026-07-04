"use client";

import { useEffect, useState } from "react";

interface LifecycleEvent {
  id: number;
  trade_id: number;
  event_type: string;
  price: number | null;
  pnl: number | null;
  notes: string | null;
  created_at: string;
}

interface Stats {
  break_even_stop_count: number;
  total_closed_trades: number;
  avg_pnl_stop_loss: number | null;
}

export default function BreakEvenPanel() {
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
          setEvents(all.filter((e) => e.event_type === "BREAK_EVEN_ACTIVATED" || e.event_type === "BREAK_EVEN_STOP"));
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

  const beStopCount = stats?.break_even_stop_count ?? 0;
  const total       = stats?.total_closed_trades ?? 0;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4">
      <h2 className="text-sm font-semibold text-white mb-3">Break Even Engine</h2>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-blue-400">{beStopCount}</div>
          <div className="text-[10px] text-[#6b7280]">Fechados por BE</div>
        </div>
        <div className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
          <div className="text-lg font-bold text-white">
            {total > 0 ? ((beStopCount / total) * 100).toFixed(1) : "0.0"}%
          </div>
          <div className="text-[10px] text-[#6b7280]">Taxa BE Stop</div>
        </div>
      </div>

      {/* Events */}
      {events.length === 0 ? (
        <p className="text-xs text-[#6b7280]">Nenhum evento de break even ainda.</p>
      ) : (
        <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
          {events.map((e) => (
            <div key={e.id} className="bg-[#0d1117] border border-[#1f2937] rounded-lg px-3 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      e.event_type === "BREAK_EVEN_STOP"
                        ? "bg-amber-900/40 text-amber-400 border border-amber-800/40"
                        : "bg-blue-900/40 text-blue-400 border border-blue-800/40"
                    }`}
                  >
                    {e.event_type === "BREAK_EVEN_STOP" ? "BE STOP" : "BE ATIVO"}
                  </span>
                  <span className="text-xs text-white">Trade #{e.trade_id}</span>
                </div>
                <span className="text-[10px] text-[#6b7280]">
                  {new Date(e.created_at).toLocaleTimeString("pt-BR")}
                </span>
              </div>
              {e.price != null && (
                <div className="mt-1 text-[10px] text-[#9ca3af]">
                  entry=${(e.price ?? 0).toFixed(2)}
                  {e.notes && <span className="ml-2 text-[#6b7280]">{e.notes}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
