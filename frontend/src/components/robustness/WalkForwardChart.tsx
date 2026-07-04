"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface PhaseMetrics {
  phase: string;
  n_trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe: number;
  expectancy: number;
  max_drawdown: number;
  sufficient: boolean;
}

interface WalkForwardData {
  symbol?: string;
  n_trades_total: number;
  train_days: number;
  val_days: number;
  test_days: number;
  train?: PhaseMetrics;
  validation?: PhaseMetrics;
  test?: PhaseMetrics;
  wr_degradation: number;
  pf_degradation: number;
  dd_increase: number;
  wf_score: number;
  is_robust: boolean;
}

function MetricCell({ label, value, unit = "" }: { label: string; value?: number; unit?: string }) {
  if (value === undefined) return <div className="text-center"><span className="text-[#4b5563]">—</span></div>;
  return (
    <div className="text-center">
      <p className="text-[10px] text-[#6b7280] mb-0.5">{label}</p>
      <p className="text-sm font-mono font-semibold text-[#f9fafb]">
        {value.toFixed(1)}{unit}
      </p>
    </div>
  );
}

function PhaseCard({ label, data, color }: { label: string; data?: PhaseMetrics; color: string }) {
  return (
    <div className="bg-[#0f1623] rounded-lg p-3 border border-[#1f2937]">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold" style={{ color }}>{label}</span>
        {data && (
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: color + "22", color }}>
            n={data.n_trades}
          </span>
        )}
      </div>
      {data ? (
        <div className="grid grid-cols-3 gap-2">
          <MetricCell label="WR %" value={data.win_rate} unit="%" />
          <MetricCell label="PF" value={data.profit_factor} />
          <MetricCell label="DD %" value={data.max_drawdown} unit="%" />
        </div>
      ) : (
        <p className="text-xs text-[#4b5563] text-center">Sem dados</p>
      )}
    </div>
  );
}

export function WalkForwardChart({ refresh }: { refresh?: number }) {
  const [data, setData] = useState<WalkForwardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/robustness/walk-forward`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  const scoreColor = (data?.wf_score ?? 0) >= 60 ? "#22c55e" : (data?.wf_score ?? 0) >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Walk Forward Validation</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `${data.train_days}d treino · ${data.val_days}d val · ${data.test_days}d teste` : "—"}
          </p>
        </div>
        {data && (
          <div className="flex items-center gap-2">
            <span
              className="px-2 py-0.5 rounded text-xs font-bold"
              style={{ background: scoreColor + "22", color: scoreColor }}
            >
              {data.wf_score.toFixed(0)} pts
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold ${data.is_robust ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
              {data.is_robust ? "ROBUSTO" : "FRÁGIL"}
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Calculando...</p>
      ) : !data || data.n_trades_total === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Dados insuficientes</p>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            <PhaseCard label="Treino"     data={data.train}      color="#60a5fa" />
            <PhaseCard label="Validação"  data={data.validation} color="#a78bfa" />
            <PhaseCard label="Teste"      data={data.test}       color="#34d399" />
          </div>
          <div className="grid grid-cols-3 gap-3 mt-1">
            {[
              { label: "Degradação WR", value: data.wr_degradation, bad: data.wr_degradation > 10 },
              { label: "Degradação PF", value: data.pf_degradation, bad: data.pf_degradation > 0.3 },
              { label: "Aumento DD",    value: data.dd_increase,    bad: data.dd_increase > 5 },
            ].map(({ label, value, bad }) => (
              <div key={label} className={`rounded-lg p-2 text-center border ${bad ? "border-red-500/30 bg-red-500/5" : "border-[#1f2937] bg-[#0f1623]"}`}>
                <p className="text-[10px] text-[#6b7280]">{label}</p>
                <p className={`text-sm font-mono font-semibold ${bad ? "text-red-400" : "text-green-400"}`}>
                  {value > 0 ? "+" : ""}{value.toFixed(1)}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
