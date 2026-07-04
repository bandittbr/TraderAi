"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface MonteCarloData {
  ruin_probability: number;
  dd_p95: number;
  dd_p99: number;
  dd_max_observed: number;
  ruin_threshold: number;
  n_trades: number;
  n_simulations: number;
}

function RiskMeter({ value, max, color, label }: { value: number; max: number; color: string; label: string }) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <span className="text-xs text-[#9ca3af]">{label}</span>
        <span className="text-xs font-mono font-semibold" style={{ color }}>
          {value.toFixed(2)}%
        </span>
      </div>
      <div className="h-2 bg-[#1f2937] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
    </div>
  );
}

export function RiskOfRuin({ refresh }: { refresh?: number }) {
  const [data, setData] = useState<MonteCarloData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/robustness/monte-carlo`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [refresh]);

  function ruinColor(p: number): string {
    if (p < 5) return "#22c55e";
    if (p < 15) return "#f59e0b";
    if (p < 30) return "#f97316";
    return "#ef4444";
  }

  function ruinLabel(p: number): string {
    if (p < 5) return "Risco Baixo";
    if (p < 15) return "Risco Moderado";
    if (p < 30) return "Risco Alto";
    return "CRÍTICO";
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Risco de Ruína</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `Limiar: ${data.ruin_threshold}% de drawdown` : "—"}
          </p>
        </div>
        {data && data.n_trades > 0 && (
          <span
            className="text-xs px-2 py-0.5 rounded font-bold"
            style={{
              background: ruinColor(data.ruin_probability) + "22",
              color: ruinColor(data.ruin_probability),
            }}
          >
            {ruinLabel(data.ruin_probability)}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Calculando...</p>
      ) : !data || data.n_trades === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-4">Dados insuficientes</p>
      ) : (
        <>
          {/* Medidor de ruína principal */}
          <div className="flex items-center justify-center py-4">
            <div className="relative w-32 h-32">
              {/* Semicírculo de fundo */}
              <svg viewBox="0 0 100 60" className="w-full">
                <path d="M 5 55 A 45 45 0 0 1 95 55" fill="none" stroke="#1f2937" strokeWidth="10" strokeLinecap="round" />
                <path
                  d="M 5 55 A 45 45 0 0 1 95 55"
                  fill="none"
                  stroke={ruinColor(data.ruin_probability)}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray="141.37"
                  strokeDashoffset={141.37 * (1 - Math.min(data.ruin_probability / 50, 1))}
                  style={{ transition: "stroke-dashoffset 0.8s ease" }}
                />
              </svg>
              <div className="absolute bottom-0 left-0 right-0 text-center">
                <p className="text-2xl font-bold tabular-nums" style={{ color: ruinColor(data.ruin_probability) }}>
                  {data.ruin_probability.toFixed(1)}%
                </p>
                <p className="text-[10px] text-[#6b7280]">probabilidade</p>
              </div>
            </div>
          </div>

          {/* Barras de drawdown */}
          <div>
            <RiskMeter
              label="Drawdown P95"
              value={data.dd_p95}
              max={60}
              color={data.dd_p95 > 20 ? "#ef4444" : "#60a5fa"}
            />
            <RiskMeter
              label="Drawdown P99"
              value={data.dd_p99}
              max={60}
              color={data.dd_p99 > 30 ? "#ef4444" : "#a78bfa"}
            />
            <RiskMeter
              label="Máximo observado"
              value={data.dd_max_observed}
              max={60}
              color={data.dd_max_observed > 40 ? "#ef4444" : "#f97316"}
            />
          </div>

          <p className="text-[10px] text-[#4b5563] text-center">
            Baseado em {data.n_simulations.toLocaleString()} simulações · seed fixo (reprodutível)
          </p>
        </>
      )}
    </div>
  );
}
