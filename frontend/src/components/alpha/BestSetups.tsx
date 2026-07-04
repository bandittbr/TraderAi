/**
 * Fase 9 — Alpha: Top Setups (padrões com maior win rate + PF)
 */
"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface PatternStats {
  pattern_key:    string;
  criteria:       string[];
  criteria_count: number;
  resolved:       number;
  win_rate:       number;
  profit_factor:  number;
  expectancy:     number;
  alpha_score:    number;
  is_positive:    boolean;
  sufficient_data: boolean;
}

export function BestSetups() {
  const [patterns, setPatterns] = useState<PatternStats[]>([]);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/alpha/best-setups?limit=15`);
        if (res.ok) setPatterns(await res.json());
      } catch {}
      finally { setLoading(false); }
    }
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-[#f9fafb] mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
        Top Setups — Alpha Positivo
      </h3>

      {loading ? (
        <div className="text-xs text-[#6b7280] text-center py-6">Calculando padrões…</div>
      ) : patterns.length === 0 ? (
        <div className="text-xs text-[#4b5563] text-center py-6">
          Dados insuficientes — aguardando histórico de sinais resolvidos.
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1">
          {patterns.map((p, i) => (
            <div
              key={p.pattern_key}
              className="flex items-start gap-3 p-3 bg-[#0f1623] rounded-lg border border-[#1f2937]"
            >
              <span className="text-xs font-bold text-[#6b7280] w-5 shrink-0">#{i + 1}</span>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap gap-1 mb-2">
                  {p.criteria.map((c) => (
                    <span
                      key={c}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono"
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div className="flex gap-4 text-xs text-[#9ca3af]">
                  <span>WR <strong className="text-emerald-400">{p.win_rate.toFixed(1)}%</strong></span>
                  <span>PF <strong className="text-blue-400">{p.profit_factor.toFixed(2)}</strong></span>
                  <span>n={p.resolved}</span>
                  <span className="ml-auto text-[10px] text-amber-400">
                    α {p.alpha_score.toFixed(1)}
                  </span>
                </div>
                {/* Barra de alpha_score */}
                <div className="mt-1.5 h-1 bg-[#1f2937] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${Math.min(p.alpha_score, 100)}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
