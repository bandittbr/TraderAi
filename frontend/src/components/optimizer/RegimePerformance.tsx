"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface RegimeCriterionStats {
  criterion: string;
  regime: string;
  sample_size: number;
  win_rate: number;
  profit_factor: number;
  recommended: boolean;
  avoid: boolean;
}

interface RegimeData {
  regime: string;
  total_signals: number;
  baseline_wr: number;
  baseline_pf: number;
  best_criteria: string[];
  avoid_criteria: string[];
  criteria_stats: RegimeCriterionStats[];
}

interface RegimeReport {
  regimes: Record<string, RegimeData>;
  total_rows: number;
}

const REGIME_CONFIG: Record<string, { label: string; color: string; dot: string }> = {
  BULL:           { label: "Bull Market",    color: "text-emerald-400", dot: "bg-emerald-500" },
  BEAR:           { label: "Bear Market",    color: "text-red-400",     dot: "bg-red-500" },
  SIDEWAYS:       { label: "Sideways",       color: "text-amber-400",   dot: "bg-amber-500" },
  HIGH_VOLATILITY:{ label: "Alta Volatil.", color: "text-purple-400",  dot: "bg-purple-500" },
  UNKNOWN:        { label: "Indefinido",     color: "text-[#6b7280]",   dot: "bg-[#6b7280]" },
};

const CRITERION_LABELS: Record<string, string> = {
  ema_cross: "EMA Cross", ema_macro: "EMA Macro", ema_price: "EMA Price",
  macd_trend: "MACD Trend", macd_signal: "MACD Signal", rsi: "RSI",
  structure: "Structure", bos: "BOS", sr_zone: "S/R Zone",
  sweep: "Sweep", fvg: "FVG", hvn_lvn: "HVN/LVN", liquidity: "Liquidity",
};

export function RegimePerformance() {
  const [data, setData] = useState<RegimeReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeRegime, setActiveRegime] = useState<string>("BULL");

  async function load() {
    try {
      const r = await fetch(`${API_BASE}/optimizer/regime?lookback_days=90`);
      if (r.ok) {
        const d: RegimeReport = await r.json();
        setData(d);
        const firstKey = Object.keys(d.regimes)[0];
        if (firstKey) setActiveRegime(firstKey);
      }
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const regimes = Object.keys(data?.regimes ?? {});
  const active  = data?.regimes[activeRegime];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Performance por Regime</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `${data.total_rows} sinais resolvidos` : "—"}
          </p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-mono">Regime</span>
      </div>

      {/* Regime tabs */}
      {regimes.length > 0 && (
        <div className="flex gap-1 mb-4 flex-wrap">
          {regimes.map((r) => {
            const cfg = REGIME_CONFIG[r] ?? { label: r, color: "text-[#9ca3af]", dot: "bg-[#6b7280]" };
            const rd  = data!.regimes[r];
            return (
              <button
                key={r}
                onClick={() => setActiveRegime(r)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium transition-colors ${
                  activeRegime === r
                    ? "bg-[#1f2937] text-[#f9fafb] border border-[#374151]"
                    : "text-[#6b7280] hover:text-[#9ca3af] hover:bg-[#1f2937]/50"
                }`}
              >
                <div className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
                {cfg.label}
                <span className="text-[9px] text-[#4b5563]">({rd.total_signals})</span>
              </button>
            );
          })}
        </div>
      )}

      {loading && <p className="text-xs text-[#6b7280] text-center py-4">Carregando…</p>}

      {!loading && !active && (
        <p className="text-xs text-[#6b7280] text-center py-4">Acumulando histórico…</p>
      )}

      {!loading && active && (
        <div className="space-y-3">
          {/* Baseline */}
          <div className="flex gap-3">
            <div className="flex-1 bg-[#0f1623] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280]">Win Rate Baseline</p>
              <p className="text-lg font-bold text-[#f9fafb]">{active.baseline_wr.toFixed(1)}%</p>
            </div>
            <div className="flex-1 bg-[#0f1623] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280]">Profit Factor</p>
              <p className="text-lg font-bold text-[#f9fafb]">{active.baseline_pf.toFixed(2)}</p>
            </div>
            <div className="flex-1 bg-[#0f1623] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280]">Sinais</p>
              <p className="text-lg font-bold text-[#f9fafb]">{active.total_signals}</p>
            </div>
          </div>

          {/* Best / Avoid */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2.5">
              <p className="text-[10px] text-emerald-400 font-semibold mb-1.5">✓ Recomendados</p>
              {active.best_criteria.length === 0
                ? <p className="text-[10px] text-[#6b7280]">—</p>
                : active.best_criteria.map((c) => (
                  <p key={c} className="text-[10px] text-emerald-300">
                    {CRITERION_LABELS[c] ?? c}
                  </p>
                ))
              }
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-2.5">
              <p className="text-[10px] text-red-400 font-semibold mb-1.5">✗ Evitar</p>
              {active.avoid_criteria.length === 0
                ? <p className="text-[10px] text-[#6b7280]">—</p>
                : active.avoid_criteria.map((c) => (
                  <p key={c} className="text-[10px] text-red-300">
                    {CRITERION_LABELS[c] ?? c}
                  </p>
                ))
              }
            </div>
          </div>

          {/* Criteria table */}
          {active.criteria_stats.length > 0 && (
            <div className="bg-[#0f1623] rounded-lg overflow-hidden">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-[#1f2937]">
                    <th className="text-left px-2 py-1.5 text-[#6b7280] font-normal">Critério</th>
                    <th className="text-right px-2 py-1.5 text-[#6b7280] font-normal">WR</th>
                    <th className="text-right px-2 py-1.5 text-[#6b7280] font-normal">PF</th>
                    <th className="text-right px-2 py-1.5 text-[#6b7280] font-normal">N</th>
                  </tr>
                </thead>
                <tbody>
                  {active.criteria_stats.slice(0, 8).map((s) => (
                    <tr key={s.criterion} className="border-b border-[#1f2937]/50">
                      <td className="px-2 py-1 text-[#9ca3af]">
                        {CRITERION_LABELS[s.criterion] ?? s.criterion}
                        {s.recommended && <span className="ml-1 text-emerald-500">●</span>}
                        {s.avoid && <span className="ml-1 text-red-500">●</span>}
                      </td>
                      <td className={`text-right px-2 py-1 font-medium ${s.win_rate >= active.baseline_wr ? "text-emerald-400" : "text-red-400"}`}>
                        {s.win_rate.toFixed(1)}%
                      </td>
                      <td className={`text-right px-2 py-1 font-medium ${s.profit_factor >= active.baseline_pf ? "text-emerald-400" : "text-red-400"}`}>
                        {s.profit_factor.toFixed(2)}
                      </td>
                      <td className="text-right px-2 py-1 text-[#6b7280]">{s.sample_size}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
