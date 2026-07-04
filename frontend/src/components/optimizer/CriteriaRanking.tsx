"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface CriterionStats {
  criterion: string;
  sample_size: number;
  resolved: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  sharpe: number;
  max_drawdown: number;
  sufficient_data: boolean;
}

interface CriteriaReport {
  criteria: CriterionStats[];
  baseline_wr: number;
  baseline_pf: number;
  total_resolved: number;
  top_criteria: string[];
  worst_criteria: string[];
}

const CRITERION_LABELS: Record<string, string> = {
  ema_cross: "EMA Cross 9/21",
  ema_macro: "EMA Macro 21/50",
  ema_price: "EMA Price 50/200",
  macd_trend: "MACD Trend",
  macd_signal: "MACD Signal",
  rsi: "RSI Zone",
  structure: "Market Structure",
  bos: "BOS / CHoCH",
  sr_zone: "S/R Zone",
  sweep: "Liquidity Sweep",
  fvg: "Fair Value Gap",
  hvn_lvn: "HVN / LVN",
  liquidity: "Liquidity Score",
};

function PFBar({ pf, baseline }: { pf: number; baseline: number }) {
  const pct = Math.min(100, (pf / 3) * 100);
  const isAbove = pf >= baseline;
  return (
    <div className="w-full bg-[#0f1623] rounded-full h-1.5 mt-1">
      <div
        className={`h-1.5 rounded-full transition-all ${isAbove ? "bg-emerald-500" : "bg-red-500"}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export function CriteriaRanking() {
  const [data, setData] = useState<CriteriaReport | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const r = await fetch(`${API_BASE}/optimizer/criteria?lookback_days=90`);
      if (r.ok) setData(await r.json());
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 300_000); // 5 min
    return () => clearInterval(id);
  }, []);

  const sorted = data?.criteria
    .filter((c) => c.sufficient_data)
    .sort((a, b) => b.profit_factor * (b.win_rate / 100) - a.profit_factor * (a.win_rate / 100))
    ?? [];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Ranking de Critérios</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `${data.total_resolved} sinais resolvidos · baseline WR ${data.baseline_wr.toFixed(1)}%` : "—"}
          </p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-purple-500/20 text-purple-400 font-mono">Fase 8</span>
      </div>

      {loading && <p className="text-xs text-[#6b7280] text-center py-4">Carregando…</p>}

      {!loading && sorted.length === 0 && (
        <p className="text-xs text-[#6b7280] text-center py-4">
          Dados insuficientes — acumulando histórico de sinais…
        </p>
      )}

      {!loading && sorted.length > 0 && (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
          {sorted.map((c, idx) => {
            const label = CRITERION_LABELS[c.criterion] ?? c.criterion;
            const isTop = data?.top_criteria.includes(c.criterion);
            const isWorst = data?.worst_criteria.includes(c.criterion);
            return (
              <div key={c.criterion} className="bg-[#0f1623] rounded-lg p-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#4b5563] font-mono w-4">#{idx + 1}</span>
                    <span className="text-xs font-medium text-[#f9fafb]">{label}</span>
                    {isTop && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400">TOP</span>
                    )}
                    {isWorst && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/20 text-red-400">EVITAR</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-right">
                    <div>
                      <p className="text-[10px] text-[#6b7280]">WR</p>
                      <p className={`text-xs font-semibold ${c.win_rate >= (data?.baseline_wr ?? 50) ? "text-emerald-400" : "text-red-400"}`}>
                        {c.win_rate.toFixed(1)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-[#6b7280]">PF</p>
                      <p className={`text-xs font-semibold ${c.profit_factor >= (data?.baseline_pf ?? 1) ? "text-emerald-400" : "text-red-400"}`}>
                        {c.profit_factor.toFixed(2)}
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-[#6b7280]">N</p>
                      <p className="text-xs text-[#9ca3af]">{c.resolved}</p>
                    </div>
                  </div>
                </div>
                <PFBar pf={c.profit_factor} baseline={data?.baseline_pf ?? 1} />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
