/**
 * Fase 9 — Alpha: Heatmap de performance por critério × regime
 */
"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface PatternStats {
  pattern_key:   string;
  criteria:      string[];
  win_rate:      number;
  profit_factor: number;
  resolved:      number;
  alpha_score:   number;
  sufficient_data: boolean;
}

interface AlphaReport {
  single_criteria: PatternStats[];
  baseline_wr:     number;
  baseline_pf:     number;
  total_resolved:  number;
}

function cellColor(wr: number, baseline: number): string {
  const diff = wr - baseline;
  if (diff > 15) return "#059669";   // muito bom
  if (diff > 5)  return "#10b981";   // bom
  if (diff > 0)  return "#34d399";   // levemente positivo
  if (diff > -5) return "#f97316";   // levemente negativo
  if (diff > -15) return "#ef4444";  // ruim
  return "#7f1d1d";                  // muito ruim
}

const SHORT_LABELS: Record<string, string> = {
  ema_bull: "EMA↑", ema_bear: "EMA↓", ema_macro_bull: "EMAm↑", ema_macro_bear: "EMAm↓",
  ema_price_above: "Px>EMA", ema_price_below: "Px<EMA",
  macd_positive: "MACD+", macd_negative: "MACD-", macd_cross: "MACDx↑", macd_cross_down: "MACDx↓",
  rsi_ok: "RSI✓", rsi_high: "RSI⚠",
  structure_bullish: "STR↑", structure_bearish: "STR↓",
  bos_bullish: "BOS↑", bos_bearish: "BOS↓",
  price_near_support: "S/R↑", price_near_resistance: "S/R↓",
  buy_side_sweep: "Swp↑", sell_side_sweep: "Swp↓",
  bullish_fvg: "FVG↑", bearish_fvg: "FVG↓",
  near_hvn_support: "HVN", near_lvn_resistance: "LVN",
  liq_score_strong_buy: "Liq↑", liq_score_strong_sell: "Liq↓",
};

export function AlphaHeatmap() {
  const [report,  setReport]  = useState<AlphaReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/alpha/patterns`);
        if (res.ok) setReport(await res.json());
      } catch {}
      finally { setLoading(false); }
    }
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const criteria = (report?.single_criteria ?? []).filter(p => p.sufficient_data && p.resolved >= 3);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-400 inline-block" />
          Heatmap de Performance por Critério
        </h3>
        {report && (
          <span className="text-[10px] text-[#6b7280]">
            Baseline {report.baseline_wr.toFixed(1)}%
          </span>
        )}
      </div>

      {loading ? (
        <div className="text-xs text-[#6b7280] text-center py-6">Gerando heatmap…</div>
      ) : criteria.length === 0 ? (
        <div className="text-xs text-[#4b5563] text-center py-6">
          Dados insuficientes — aguardando histórico.
        </div>
      ) : (
        <>
          {/* Legenda */}
          <div className="flex gap-2 mb-3 flex-wrap">
            {[
              { color: "#059669", label: "WR +15%" },
              { color: "#10b981", label: "+5%" },
              { color: "#34d399", label: "+0%" },
              { color: "#f97316", label: "-5%" },
              { color: "#ef4444", label: "-15%" },
            ].map(({ color, label }) => (
              <div key={label} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded-sm" style={{ background: color }} />
                <span className="text-[10px] text-[#6b7280]">{label}</span>
              </div>
            ))}
          </div>

          {/* Grid heatmap */}
          <div className="flex flex-wrap gap-2">
            {criteria.map((p) => {
              const label = SHORT_LABELS[p.pattern_key] ?? p.pattern_key.slice(0, 8);
              const bg    = cellColor(p.win_rate, report!.baseline_wr);
              return (
                <div
                  key={p.pattern_key}
                  className="flex flex-col items-center justify-center rounded-md p-2 min-w-[64px] cursor-default"
                  style={{ background: bg + "33", border: `1px solid ${bg}66` }}
                  title={`${p.pattern_key}\nWR: ${p.win_rate.toFixed(1)}%\nPF: ${p.profit_factor.toFixed(2)}\nn=${p.resolved}`}
                >
                  <span className="text-[10px] font-mono text-[#e5e7eb] text-center leading-tight">{label}</span>
                  <span className="text-xs font-bold mt-0.5" style={{ color: bg }}>{p.win_rate.toFixed(0)}%</span>
                  <span className="text-[10px] text-[#6b7280]">n={p.resolved}</span>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
