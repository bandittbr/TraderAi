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

export default function TrailingStopPanel() {
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/v1/trade-management/events?limit=100");
        if (r.ok) {
          const all: LifecycleEvent[] = await r.json();
          setEvents(all.filter((e) => e.event_type === "TRAILING_UPDATED" || e.event_type === "TRAILING_STOP"));
        }
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
      <h2 className="text-sm font-semibold text-white mb-3">
        Trailing Stop Engine
        <span className="ml-2 text-xs text-[#6b7280]">({events.length} eventos)</span>
      </h2>

      {events.length === 0 ? (
        <p className="text-xs text-[#6b7280]">Nenhum evento de trailing stop ainda.</p>
      ) : (
        <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
          {events.map((e) => (
            <div key={e.id} className="bg-[#0d1117] border border-[#1f2937] rounded-lg px-3 py-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      e.event_type === "TRAILING_STOP"
                        ? "bg-red-900/40 text-red-400 border border-red-800/40"
                        : "bg-purple-900/40 text-purple-400 border border-purple-800/40"
                    }`}
                  >
                    {e.event_type === "TRAILING_STOP" ? "HIT" : "UPDATE"}
                  </span>
                  <span className="text-xs text-white">
                    Trade #{e.trade_id}
                  </span>
                </div>
                <span className="text-[10px] text-[#6b7280]">
                  {new Date(e.created_at).toLocaleTimeString("pt-BR")}
                </span>
              </div>
              {e.price != null && (
                <div className="mt-1 text-[10px] text-[#9ca3af]">
                  stop=${(e.price ?? 0).toFixed(2)}
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
