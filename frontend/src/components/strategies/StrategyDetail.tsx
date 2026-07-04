"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Strategy {
  id: number;
  name: string;
  strategy_key: string;
  generation: number;
  origin: string;
  status: string;
  win_rate: number;
  profit_factor: number;
  sharpe: number;
  calmar: number;
  expectancy: number;
  max_drawdown: number;
  n_trades: number;
  strategy_score: number;
  rank_position?: number;
  wf_score?: number;
  mc_ruin_prob?: number;
  stability_score?: number;
  robustness_score?: number;
  is_robust: boolean;
  rejection_reason?: string;
  entry_rules: Record<string, unknown>;
  exit_rules:  Record<string, unknown>;
  risk_rules:  Record<string, unknown>;
  parent_ids: string[];
  created_at: string;
}

function MetricBox({ label, value, unit = "", warn }: { label: string; value?: number | null; unit?: string; warn?: boolean }) {
  return (
    <div className="bg-[#0f1623] rounded-lg p-3 text-center border border-[#1f2937]">
      <p className="text-[10px] text-[#6b7280] mb-1">{label}</p>
      <p className={`text-sm font-mono font-bold ${warn ? "text-red-400" : "text-[#f9fafb]"}`}>
        {value != null ? `${value.toFixed(2)}${unit}` : "—"}
      </p>
    </div>
  );
}

function RuleChip({ label, value }: { label: string; value: unknown }) {
  const display = typeof value === "boolean"
    ? (value ? "✓" : "✗")
    : typeof value === "object"
    ? JSON.stringify(value)
    : String(value);
  const isOn = value === true;
  return (
    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold mr-1 mb-1 ${
      isOn ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25"
           : "bg-[#1f2937] text-[#6b7280]"}`}>
      {label}: {display}
    </div>
  );
}

export function StrategyDetail({ strategyId }: { strategyId: number | null }) {
  const [data, setData] = useState<Strategy | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!strategyId) { setData(null); return; }
    setLoading(true);
    fetch(`${API_BASE}/strategies/${strategyId}`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [strategyId]);

  if (!strategyId) return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex items-center justify-center min-h-48">
      <p className="text-xs text-[#4b5563]">Selecione uma estratégia no ranking para ver os detalhes</p>
    </div>
  );

  if (loading) return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex items-center justify-center min-h-48">
      <p className="text-xs text-[#4b5563]">Carregando...</p>
    </div>
  );

  if (!data) return null;

  const statusColor = data.status === "APPROVED" ? "text-green-400 bg-green-500/10"
    : data.status === "TESTING" ? "text-blue-400 bg-blue-500/10"
    : data.status === "REJECTED" ? "text-red-400 bg-red-500/10"
    : "text-[#9ca3af] bg-[#1f2937]";

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h2 className="text-sm font-semibold text-[#f9fafb] truncate">{data.name}</h2>
          <p className="text-[10px] text-[#4b5563] font-mono mt-0.5">{data.strategy_key}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${statusColor}`}>{data.status}</span>
          {data.rank_position && (
            <span className="text-[10px] text-[#9ca3af]">#{data.rank_position}</span>
          )}
        </div>
      </div>

      {/* Métricas */}
      <div className="grid grid-cols-4 gap-2">
        <MetricBox label="Score"        value={data.strategy_score} />
        <MetricBox label="Win Rate"     value={data.win_rate}       unit="%" />
        <MetricBox label="Profit Factor" value={data.profit_factor} />
        <MetricBox label="Sharpe"       value={data.sharpe}         />
        <MetricBox label="Calmar"       value={data.calmar}         />
        <MetricBox label="Expectancy"   value={data.expectancy}     unit="%" />
        <MetricBox label="Max DD"       value={data.max_drawdown}   unit="%" warn={data.max_drawdown > 20} />
        <MetricBox label="Trades"       value={data.n_trades}       unit="" />
      </div>

      {/* Robustez */}
      {data.robustness_score != null && (
        <div className="bg-[#0f1623] rounded-lg p-3 border border-[#1f2937]">
          <p className="text-[10px] text-[#6b7280] font-semibold uppercase tracking-wider mb-2">Robustez</p>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div><p className="text-[9px] text-[#6b7280]">Walk Forward</p><p className="text-xs font-mono text-[#f9fafb]">{(data.wf_score ?? 0).toFixed(1)}</p></div>
            <div><p className="text-[9px] text-[#6b7280]">Risco Ruína</p><p className={`text-xs font-mono ${(data.mc_ruin_prob ?? 0) > 20 ? "text-red-400" : "text-green-400"}`}>{(data.mc_ruin_prob ?? 0).toFixed(1)}%</p></div>
            <div><p className="text-[9px] text-[#6b7280]">Estabilidade</p><p className="text-xs font-mono text-[#f9fafb]">{(data.stability_score ?? 0).toFixed(1)}</p></div>
          </div>
        </div>
      )}

      {/* Entry Rules */}
      <div>
        <p className="text-[10px] text-[#6b7280] font-semibold uppercase tracking-wider mb-1.5">Entry Rules</p>
        <div className="flex flex-wrap">
          {Object.entries(data.entry_rules).map(([k, v]) => <RuleChip key={k} label={k} value={v} />)}
        </div>
      </div>

      {/* Exit + Risk */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[10px] text-[#6b7280] font-semibold uppercase tracking-wider mb-1.5">Exit Rules</p>
          <div className="flex flex-wrap">
            {Object.entries(data.exit_rules).map(([k, v]) => <RuleChip key={k} label={k} value={v} />)}
          </div>
        </div>
        <div>
          <p className="text-[10px] text-[#6b7280] font-semibold uppercase tracking-wider mb-1.5">Risk Rules</p>
          <div className="flex flex-wrap">
            {Object.entries(data.risk_rules).map(([k, v]) => <RuleChip key={k} label={k} value={v} />)}
          </div>
        </div>
      </div>

      {data.rejection_reason && (
        <div className="bg-red-500/5 border border-red-500/20 rounded-lg px-3 py-2">
          <p className="text-[10px] text-red-400">Motivo rejeição: {data.rejection_reason}</p>
        </div>
      )}

      <p className="text-[9px] text-[#4b5563]">
        Geração {data.generation} · {data.origin} · Criada {new Date(data.created_at).toLocaleDateString("pt-BR")}
        {data.parent_ids.length > 0 && ` · Pais: ${data.parent_ids.length}`}
      </p>
    </div>
  );
}
