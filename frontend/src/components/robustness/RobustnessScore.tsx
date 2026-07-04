"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface RobustnessRun {
  status: string;
  symbol?: string;
  pattern_key?: string;
  robustness_score: number;
  interpretation: string;
  computed_at: string;
}

function scoreColor(score: number): string {
  if (score >= 75) return "#22c55e";
  if (score >= 55) return "#f59e0b";
  if (score >= 35) return "#f97316";
  return "#ef4444";
}

function interpLabel(s: string): string {
  const m: Record<string, string> = {
    ROBUSTO: "Robusto",
    MODERADO: "Moderado",
    FRAGIL: "Frágil",
    ALTO_RISCO: "Alto Risco",
    DADOS_INSUFICIENTES: "Dados insuficientes",
  };
  return m[s] ?? s;
}

export function RobustnessScore({ onRun }: { onRun?: () => void }) {
  const [data, setData] = useState<RobustnessRun | null>(null);
  const [loading, setLoading] = useState(false);

  async function runAnalysis() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/robustness/run`, { method: "POST" });
      if (res.ok) {
        const json = await res.json();
        setData(json);
        onRun?.();
      }
    } catch {}
    setLoading(false);
  }

  useEffect(() => {
    fetch(`${API_BASE}/robustness/report`)
      .then((r) => r.json())
      .then((d) => {
        if (d?.robustness_score !== undefined) {
          setData({
            status: "ok",
            symbol: d.symbol,
            pattern_key: d.pattern_key,
            robustness_score: d.robustness_score,
            interpretation: d.interpretation,
            computed_at: d.computed_at,
          });
        }
      })
      .catch(() => {});
  }, []);

  const score = data?.robustness_score ?? 0;
  const color = scoreColor(score);
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Robustness Score</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">Walk Forward · Monte Carlo · Estabilidade</p>
        </div>
        <button
          onClick={runAnalysis}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-semibold rounded-md bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30 transition-colors disabled:opacity-50"
        >
          {loading ? "Calculando..." : "Rodar Análise"}
        </button>
      </div>

      <div className="flex items-center gap-6">
        {/* Gauge circular */}
        <div className="relative flex items-center justify-center" style={{ width: 128, height: 128 }}>
          <svg width="128" height="128" viewBox="0 0 128 128">
            <circle cx="64" cy="64" r={r} fill="none" stroke="#1f2937" strokeWidth="10" />
            <circle
              cx="64" cy="64" r={r}
              fill="none"
              stroke={color}
              strokeWidth="10"
              strokeDasharray={circ}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform="rotate(-90 64 64)"
              style={{ transition: "stroke-dashoffset 0.8s ease" }}
            />
          </svg>
          <div className="absolute flex flex-col items-center">
            <span className="text-2xl font-bold tabular-nums" style={{ color }}>
              {score.toFixed(0)}
            </span>
            <span className="text-[10px] text-[#6b7280]">/ 100</span>
          </div>
        </div>

        {/* Info */}
        <div className="flex flex-col gap-2">
          <div>
            <span
              className="px-2 py-0.5 rounded text-xs font-semibold"
              style={{ background: color + "22", color }}
            >
              {data ? interpLabel(data.interpretation) : "—"}
            </span>
          </div>
          {data?.symbol && (
            <p className="text-xs text-[#9ca3af]">Ativo: <span className="text-[#f9fafb]">{data.symbol}</span></p>
          )}
          {data?.computed_at && (
            <p className="text-xs text-[#4b5563]">
              {new Date(data.computed_at).toLocaleString("pt-BR")}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
