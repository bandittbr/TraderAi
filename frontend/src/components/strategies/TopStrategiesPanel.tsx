"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Strategy {
  id: number;
  name: string;
  strategy_score: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  n_trades: number;
  rank_position?: number;
  mc_ruin_prob?: number;
  robustness_score?: number;
}

export function TopStrategiesPanel({
  refresh,
  onSelect,
}: {
  refresh?:  number;
  onSelect?: (id: number) => void;
}) {
  const [top,     setTop]     = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/strategies/top?limit=10`)
      .then((r) => r.json())
      .then(setTop)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  const maxScore = Math.max(...top.map((s) => s.strategy_score), 1);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold text-[#f9fafb]">Top 10 Estratégias Aprovadas</h2>
        <p className="text-xs text-[#6b7280] mt-0.5">Ordenadas por score composto (WR · PF · Sharpe · Calmar)</p>
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-6">Carregando...</p>
      ) : top.length === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-6">
          Nenhuma estratégia aprovada ainda.<br />
          <span className="text-[#6b7280]">Execute o Evolution Engine para iniciar a descoberta.</span>
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {top.map((s, i) => {
            const barW = (s.strategy_score / maxScore) * 100;
            const ruinOk = (s.mc_ruin_prob ?? 0) < 15;
            return (
              <div
                key={s.id}
                onClick={() => onSelect?.(s.id)}
                className="cursor-pointer hover:bg-[#1f2937]/40 rounded-lg p-2 transition-colors"
              >
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[#4b5563] w-5">#{i + 1}</span>
                    <span className="text-xs text-[#9ca3af] truncate max-w-[200px]">{s.name.slice(0, 45)}</span>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-[10px] text-[#6b7280]">WR {s.win_rate.toFixed(1)}% · PF {s.profit_factor.toFixed(2)}</span>
                    <span className={`text-[10px] px-1 py-0.5 rounded font-semibold ${ruinOk ? "text-green-400 bg-green-500/10" : "text-red-400 bg-red-500/10"}`}>
                      {ruinOk ? "✓" : "⚠"} Ruína
                    </span>
                    <span className="text-sm font-bold text-emerald-400">{s.strategy_score.toFixed(1)}</span>
                  </div>
                </div>
                {/* Barra de score */}
                <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${barW}%`,
                      background: `linear-gradient(90deg, #10b981, #34d399)`,
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
