"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

interface EvolveResult {
  status: string;
  n_generated: number;
  n_evaluated: number;
  n_approved:  number;
  n_evolved:   number;
  top_score:   number;
  top_strategy?: string;
  computed_at: string;
}

function StatCard({ label, value, color = "#f9fafb" }: { label: string; value: number; color?: string }) {
  return (
    <div className="bg-[#0f1623] rounded-lg p-3 text-center border border-[#1f2937]">
      <p className="text-[10px] text-[#6b7280] mb-1">{label}</p>
      <p className="text-xl font-bold tabular-nums" style={{ color }}>{value}</p>
    </div>
  );
}

export function EvolutionPanel({ onDone }: { onDone?: () => void }) {
  const [result,  setResult]  = useState<EvolveResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [batch,   setBatch]   = useState(200);

  async function runEvolution() {
    setLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/strategies/evolve?batch=${batch}&generate_new=true&evolve=true&validate_rob=false`,
        { method: "POST" },
      );
      if (res.ok) {
        const data = await res.json();
        setResult(data);
        onDone?.();
      }
    } catch {}
    setLoading(false);
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Evolution Engine</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">
            Generator → Evaluator → Mutação → Crossover · Determinístico (seed=42)
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={batch}
            onChange={(e) => setBatch(Number(e.target.value))}
            className="text-xs bg-[#0f1623] border border-[#1f2937] text-[#9ca3af] rounded px-2 py-1"
          >
            {[50, 100, 200, 500].map((b) => (
              <option key={b} value={b}>{b} estratégias</option>
            ))}
          </select>
          <button
            onClick={runEvolution}
            disabled={loading}
            className="px-3 py-1.5 text-xs font-semibold rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
          >
            {loading ? "Evoluindo..." : "Rodar Evolução"}
          </button>
        </div>
      </div>

      {/* Segurança */}
      <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
        <p className="text-[10px] text-amber-400 font-semibold">
          🔒 Segurança: Estratégias novas ficam em CANDIDATE.
          Apenas estratégias aprovadas por robustez entram no ranking.
          Nenhuma substitui automaticamente a estratégia ativa.
        </p>
      </div>

      {result && (
        <>
          <div className="grid grid-cols-4 gap-3">
            <StatCard label="Geradas"   value={result.n_generated} color="#60a5fa" />
            <StatCard label="Avaliadas" value={result.n_evaluated} color="#a78bfa" />
            <StatCard label="Aprovadas" value={result.n_approved}  color="#22c55e" />
            <StatCard label="Evoluídas" value={result.n_evolved}   color="#f59e0b" />
          </div>
          {result.top_strategy && (
            <div className="bg-[#0f1623] rounded-lg p-3 border border-[#1f2937]">
              <p className="text-[10px] text-[#6b7280] mb-1">Top estratégia atual</p>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#9ca3af] truncate">{result.top_strategy}</span>
                <span className="text-sm font-bold text-emerald-400 ml-3">{result.top_score.toFixed(1)} pts</span>
              </div>
            </div>
          )}
          <p className="text-[9px] text-[#4b5563] text-right">
            {new Date(result.computed_at).toLocaleString("pt-BR")}
          </p>
        </>
      )}

      {/* Pipeline visual */}
      {!result && !loading && (
        <div className="flex items-center justify-center gap-2 py-3">
          {["Gerador", "→", "Backtest", "→", "Robustez", "→", "Ranking"].map((s, i) => (
            s === "→"
              ? <span key={i} className="text-[#4b5563] text-xs">→</span>
              : <span key={i} className="text-[10px] px-2 py-1 rounded bg-[#1f2937] text-[#9ca3af] border border-[#374151]">{s}</span>
          ))}
        </div>
      )}
    </div>
  );
}
