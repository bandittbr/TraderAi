"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface WeightEntry { criterion: string; weight: number; }

interface BacktestComparison {
  v5_win_rate: number | null;
  v5_profit_factor: number | null;
  v5_sharpe: number | null;
  v5_drawdown: number | null;
  v5_signals: number;
  v6_win_rate: number | null;
  v6_profit_factor: number | null;
  v6_sharpe: number | null;
  v6_drawdown: number | null;
  v6_signals: number;
  improvement_wr: number | null;
  improvement_pf: number | null;
}

interface SummaryData {
  total_resolved: number;
  baseline_wr: number;
  baseline_pf: number;
  top_criteria: string[];
  worst_criteria: string[];
  weights: Record<string, number>;
}

const CRITERION_LABELS: Record<string, string> = {
  ema_cross: "EMA Cross",  ema_macro: "EMA Macro",  ema_price: "EMA Price",
  macd_trend: "MACD Trend", macd_signal: "MACD Sig",  rsi: "RSI",
  structure: "Structure",  bos: "BOS",              sr_zone: "S/R Zone",
  sweep: "Sweep",          fvg: "FVG",              hvn_lvn: "HVN/LVN",
  liquidity: "Liquidity",
};

function WeightBar({ weight }: { weight: number }) {
  const pct  = ((weight - 1) / 19) * 100;
  const color = weight > 12 ? "bg-emerald-500" : weight < 8 ? "bg-red-500" : "bg-blue-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-[#0a0e1a] rounded-full h-1.5">
        <div className={`h-1.5 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-[10px] font-mono w-7 text-right ${weight > 12 ? "text-emerald-400" : weight < 8 ? "text-red-400" : "text-blue-400"}`}>
        {weight.toFixed(1)}
      </span>
    </div>
  );
}

function MetricDelta({ label, v5, v6, higher }: { label: string; v5: number | null; v6: number | null; higher?: boolean }) {
  const delta = v5 != null && v6 != null ? v6 - v5 : null;
  const good  = delta == null ? null : (higher !== false ? delta >= 0 : delta <= 0);
  return (
    <div className="bg-[#0f1623] rounded-lg p-2.5">
      <p className="text-[10px] text-[#6b7280] mb-1">{label}</p>
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[9px] text-[#4b5563]">V5</p>
          <p className="text-xs text-[#9ca3af]">{v5 != null ? v5.toFixed(2) : "—"}</p>
        </div>
        <div className="text-center">
          {delta != null && (
            <span className={`text-[10px] font-semibold ${good ? "text-emerald-400" : "text-red-400"}`}>
              {delta >= 0 ? "+" : ""}{delta.toFixed(2)}
            </span>
          )}
        </div>
        <div className="text-right">
          <p className="text-[9px] text-[#4b5563]">V6</p>
          <p className={`text-xs font-semibold ${good == null ? "text-[#9ca3af]" : good ? "text-emerald-400" : "text-red-400"}`}>
            {v6 != null ? v6.toFixed(2) : "—"}
          </p>
        </div>
      </div>
    </div>
  );
}

export function OptimizerDashboard() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [bt, setBt] = useState<BacktestComparison | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const [s, b] = await Promise.all([
        fetch(`${API_BASE}/optimizer/criteria?lookback_days=90`).then(r => r.ok ? r.json() : null),
        fetch(`${API_BASE}/optimizer/backtest-compare?lookback_days=90`).then(r => r.ok ? r.json() : null),
      ]);
      const w = await fetch(`${API_BASE}/optimizer/weights`).then(r => r.ok ? r.json() : null);
      if (s) setSummary({ ...s, weights: w?.weights ?? {} });
      if (b) setBt(b);
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const weightEntries: WeightEntry[] = Object.entries(summary?.weights ?? {})
    .map(([criterion, weight]) => ({ criterion, weight }))
    .sort((a, b) => b.weight - a.weight);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Optimizer Dashboard</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {summary ? `${summary.total_resolved} sinais · WR base ${summary.baseline_wr.toFixed(1)}% · PF ${summary.baseline_pf.toFixed(2)}` : "—"}
          </p>
        </div>
        <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-mono">V6 Adaptive</span>
      </div>

      {loading && <p className="text-xs text-[#6b7280] text-center py-4">Calculando…</p>}

      {!loading && (
        <>
          {/* Top / Worst criteria badges */}
          {(summary?.top_criteria?.length ?? 0) > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-[#6b7280] uppercase tracking-wide">Melhores critérios</p>
              <div className="flex flex-wrap gap-1">
                {summary!.top_criteria.map((c) => (
                  <span key={c} className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 font-medium">
                    {CRITERION_LABELS[c] ?? c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(summary?.worst_criteria?.length ?? 0) > 0 && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-[#6b7280] uppercase tracking-wide">Critérios a evitar</p>
              <div className="flex flex-wrap gap-1">
                {summary!.worst_criteria.map((c) => (
                  <span key={c} className="text-[10px] px-2 py-0.5 rounded bg-red-500/15 text-red-400 font-medium">
                    {CRITERION_LABELS[c] ?? c}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Adaptive weights */}
          {weightEntries.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <p className="text-[10px] text-[#6b7280] uppercase tracking-wide">Pesos Adaptativos</p>
                <p className="text-[9px] text-[#4b5563]">min=1 · default=10 · max=20</p>
              </div>
              <div className="grid grid-cols-1 gap-1">
                {weightEntries.map(({ criterion, weight }) => (
                  <div key={criterion} className="flex items-center gap-2">
                    <span className="text-[10px] text-[#9ca3af] w-24 shrink-0">
                      {CRITERION_LABELS[criterion] ?? criterion}
                    </span>
                    <div className="flex-1">
                      <WeightBar weight={weight} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Backtest V5 vs V6 */}
          {bt && (
            <div className="space-y-1.5">
              <p className="text-[10px] text-[#6b7280] uppercase tracking-wide">Backtest V5 vs V6</p>
              <div className="grid grid-cols-2 gap-2">
                <MetricDelta label="Win Rate (%)" v5={bt.v5_win_rate} v6={bt.v6_win_rate} higher />
                <MetricDelta label="Profit Factor" v5={bt.v5_profit_factor} v6={bt.v6_profit_factor} higher />
                <MetricDelta label="Sharpe" v5={bt.v5_sharpe} v6={bt.v6_sharpe} higher />
                <MetricDelta label="Drawdown" v5={bt.v5_drawdown} v6={bt.v6_drawdown} higher={false} />
              </div>
              <p className="text-[9px] text-[#4b5563] text-right">
                V5: {bt.v5_signals} sinais · V6: {bt.v6_signals} sinais
              </p>
            </div>
          )}

          {!summary && !bt && (
            <p className="text-xs text-[#6b7280] text-center py-2">
              Acumulando histórico de sinais para otimização…
            </p>
          )}
        </>
      )}
    </div>
  );
}
