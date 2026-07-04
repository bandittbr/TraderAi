"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface DimensionCell {
  dimension_type: string;
  dimension_value: string;
  n_trades: number;
  win_rate: number;
  profit_factor: number;
  baseline_wr: number;
  wr_vs_baseline: number;
  stability_score: number;
  is_unstable: boolean;
  unstable_reason?: string;
}

interface StabilityData {
  n_total_trades: number;
  baseline_wr: number;
  baseline_pf: number;
  by_symbol: DimensionCell[];
  by_regime: DimensionCell[];
  by_timeframe: DimensionCell[];
  by_period: DimensionCell[];
  overall_stability_score: number;
  n_unstable_cells: number;
}

function CellRow({ cell }: { cell: DimensionCell }) {
  const color = cell.stability_score >= 70 ? "#22c55e" : cell.stability_score >= 45 ? "#f59e0b" : "#ef4444";
  return (
    <div className={`flex items-center justify-between py-2 px-3 rounded-lg mb-1 ${cell.is_unstable ? "bg-red-500/5 border border-red-500/20" : "bg-[#0f1623] border border-[#1f2937]"}`}>
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-[#f9fafb]">{cell.dimension_value}</span>
        {cell.is_unstable && (
          <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/20 text-red-400 font-semibold">UNSTABLE</span>
        )}
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-[10px] text-[#6b7280]">WR</p>
          <p className="text-xs font-mono text-[#f9fafb]">{cell.win_rate.toFixed(1)}%</p>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-[#6b7280]">Δ</p>
          <p className={`text-xs font-mono font-semibold ${cell.wr_vs_baseline >= 0 ? "text-green-400" : "text-red-400"}`}>
            {cell.wr_vs_baseline > 0 ? "+" : ""}{cell.wr_vs_baseline.toFixed(1)}pp
          </p>
        </div>
        <div className="text-right w-12">
          <p className="text-[10px] text-[#6b7280]">Score</p>
          <p className="text-xs font-mono font-semibold" style={{ color }}>
            {cell.stability_score.toFixed(0)}
          </p>
        </div>
      </div>
    </div>
  );
}

const TAB_LABELS: Record<string, string> = {
  by_symbol: "Ativo",
  by_regime: "Regime",
  by_timeframe: "Timeframe",
  by_period: "Período",
};

export function StabilityRanking({ refresh }: { refresh?: number }) {
  const [data, setData] = useState<StabilityData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<keyof StabilityData>("by_regime");

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/robustness/stability`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  const tabs = ["by_symbol", "by_regime", "by_timeframe", "by_period"] as const;
  const cells = data ? (data[tab] as DimensionCell[]) : [];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Estabilidade por Dimensão</h2>
          {data && (
            <p className="text-xs text-[#6b7280] mt-0.5">
              {data.n_total_trades} trades · baseline WR {data.baseline_wr.toFixed(1)}% ·{" "}
              {data.n_unstable_cells > 0
                ? <span className="text-red-400">{data.n_unstable_cells} instável(eis)</span>
                : <span className="text-green-400">tudo estável</span>}
            </p>
          )}
        </div>
        {data && (
          <span className={`text-xs px-2 py-0.5 rounded font-bold ${
            data.overall_stability_score >= 70 ? "bg-green-500/20 text-green-400"
            : data.overall_stability_score >= 45 ? "bg-amber-500/20 text-amber-400"
            : "bg-red-500/20 text-red-400"
          }`}>
            {data.overall_stability_score.toFixed(0)} pts
          </span>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#0f1623] p-1 rounded-lg">
        {tabs.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 text-[10px] py-1 rounded-md font-semibold transition-all ${
              tab === t ? "bg-purple-500 text-white" : "text-[#6b7280] hover:text-[#f9fafb]"
            }`}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Analisando...</p>
      ) : !data || data.n_total_trades === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Dados insuficientes</p>
      ) : cells.length === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Nenhum dado para esta dimensão</p>
      ) : (
        <div className="overflow-y-auto max-h-64">
          {cells.map((c) => <CellRow key={`${c.dimension_type}-${c.dimension_value}`} cell={c} />)}
        </div>
      )}
    </div>
  );
}
