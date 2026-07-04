"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Strategy {
  id: number;
  strategy_key: string;
  name: string;
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
  robustness_score?: number;
  mc_ruin_prob?: number;
  is_robust: boolean;
  rejection_reason?: string;
}

function scoreColor(s: number) {
  if (s >= 70) return "#22c55e";
  if (s >= 50) return "#f59e0b";
  if (s >= 30) return "#f97316";
  return "#ef4444";
}

function originBadge(origin: string) {
  const m: Record<string, string> = { GENERATED: "GEN", MUTATED: "MUT", CROSSOVER: "CRS" };
  const c: Record<string, string> = {
    GENERATED: "bg-blue-500/20 text-blue-400",
    MUTATED:   "bg-purple-500/20 text-purple-400",
    CROSSOVER: "bg-amber-500/20 text-amber-400",
  };
  return { label: m[origin] ?? origin.slice(0,3), cls: c[origin] ?? "bg-gray-500/20 text-gray-400" };
}

export function StrategyRanking({
  onSelect,
  refresh,
}: {
  onSelect?: (id: number) => void;
  refresh?:  number;
}) {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [total,      setTotal]      = useState(0);
  const [loading,    setLoading]    = useState(true);
  const [statusFilter, setFilter]   = useState<string>("APPROVED");

  useEffect(() => {
    setLoading(true);
    fetch(`${API_BASE}/strategies?status=${statusFilter}&limit=50`)
      .then((r) => r.json())
      .then((d) => { setStrategies(d.strategies ?? []); setTotal(d.total ?? 0); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [statusFilter, refresh]);

  const filters = ["APPROVED", "TESTING", "CANDIDATE", "REJECTED"];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#f9fafb]">Ranking de Estratégias</h2>
          <p className="text-xs text-[#6b7280] mt-0.5">{total} no banco · {strategies.length} exibidas</p>
        </div>
        <div className="flex gap-1">
          {filters.map((f) => (
            <button key={f} onClick={() => setFilter(f)}
              className={`text-[10px] px-2 py-0.5 rounded font-semibold transition-all ${
                statusFilter === f ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "text-[#6b7280] hover:text-[#f9fafb]"}`}>
              {f.slice(0,3)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-xs text-[#4b5563] text-center py-6">Carregando...</p>
      ) : strategies.length === 0 ? (
        <p className="text-xs text-[#4b5563] text-center py-6">
          Nenhuma estratégia em status {statusFilter}.<br />
          <span className="text-[#6b7280]">Clique em "Rodar Evolução" para iniciar a descoberta.</span>
        </p>
      ) : (
        <div className="overflow-y-auto max-h-96">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[#6b7280] border-b border-[#1f2937]">
                <th className="text-left py-1.5 pr-3">#</th>
                <th className="text-left py-1.5 pr-3">Nome</th>
                <th className="text-right py-1.5 pr-3">Score</th>
                <th className="text-right py-1.5 pr-3">WR%</th>
                <th className="text-right py-1.5 pr-3">PF</th>
                <th className="text-right py-1.5 pr-3">Sharpe</th>
                <th className="text-right py-1.5 pr-3">DD%</th>
                <th className="text-right py-1.5">n</th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((s, i) => {
                const orig = originBadge(s.origin);
                return (
                  <tr
                    key={s.id}
                    onClick={() => onSelect?.(s.id)}
                    className="border-b border-[#1f2937] hover:bg-[#1f2937]/40 cursor-pointer transition-colors"
                  >
                    <td className="py-1.5 pr-3 text-[#4b5563]">
                      {s.rank_position ?? i + 1}
                    </td>
                    <td className="py-1.5 pr-3 max-w-[180px]">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-[9px] px-1 py-0.5 rounded font-semibold ${orig.cls}`}>{orig.label}</span>
                        <span className="text-[#9ca3af] truncate text-[10px]">{s.name.slice(0,40)}</span>
                      </div>
                    </td>
                    <td className="py-1.5 pr-3 text-right font-bold tabular-nums"
                      style={{ color: scoreColor(s.strategy_score) }}>
                      {s.strategy_score.toFixed(1)}
                    </td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-[#f9fafb]">{s.win_rate.toFixed(1)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-[#f9fafb]">{s.profit_factor.toFixed(2)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-[#f9fafb]">{s.sharpe.toFixed(2)}</td>
                    <td className="py-1.5 pr-3 text-right tabular-nums text-red-400">{s.max_drawdown.toFixed(1)}</td>
                    <td className="py-1.5 text-right tabular-nums text-[#6b7280]">{s.n_trades}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
