/**
 * Fase 9 — Setup Quality Score: painel de qualidade + histórico
 */
"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface QualityEntry {
  id:                 number;
  symbol:             string;
  signal:             string | null;
  regime:             string | null;
  quality_score:      number;
  pattern_score:      number | null;
  regime_score:       number | null;
  context_score_comp: number | null;
  confluence_score:   number | null;
  criteria_count:     number | null;
  outcome:            string | null;
  pnl_pct:            number | null;
  computed_at:        string;
}

function ScoreGauge({ score }: { score: number }) {
  const color =
    score >= 75 ? "#10b981" :
    score >= 50 ? "#f59e0b" :
    score >= 30 ? "#f97316" : "#ef4444";

  return (
    <div className="relative w-20 h-20">
      <svg viewBox="0 0 80 80" className="w-full h-full -rotate-90">
        <circle cx="40" cy="40" r="32" fill="none" stroke="#1f2937" strokeWidth="8" />
        <circle
          cx="40" cy="40" r="32" fill="none"
          stroke={color} strokeWidth="8"
          strokeDasharray={`${(score / 100) * 201} 201`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-lg font-bold" style={{ color }}>{score.toFixed(0)}</span>
        <span className="text-[10px] text-[#6b7280]">score</span>
      </div>
    </div>
  );
}

export function SetupQualityPanel({ symbol }: { symbol?: string }) {
  const [entries,  setEntries]  = useState<QualityEntry[]>([]);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const url = `${API_BASE}/alpha/quality?limit=30${symbol ? `&symbol=${symbol}` : ""}`;
        const res = await fetch(url);
        if (res.ok) setEntries(await res.json());
      } catch {}
      finally { setLoading(false); }
    }
    load();
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [symbol]);

  const latest = entries[0] ?? null;
  const avgScore = entries.length
    ? entries.reduce((s, e) => s + e.quality_score, 0) / entries.length
    : 0;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-[#f9fafb] mb-4 flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" />
        Setup Quality Score
      </h3>

      {loading ? (
        <div className="text-xs text-[#6b7280] text-center py-6">Carregando…</div>
      ) : entries.length === 0 ? (
        <div className="text-xs text-[#4b5563] text-center py-6">
          Nenhum score calculado ainda.
        </div>
      ) : (
        <>
          {/* Score atual */}
          {latest && (
            <div className="flex items-center gap-5 mb-5 p-3 bg-[#0f1623] rounded-lg border border-[#1f2937]">
              <ScoreGauge score={latest.quality_score} />
              <div className="flex-1">
                <p className="text-xs text-[#6b7280] mb-1">Último Setup</p>
                <p className="text-sm font-semibold text-[#e5e7eb]">
                  {latest.symbol} — {latest.signal ?? "—"}
                </p>
                <p className="text-xs text-[#6b7280] mt-1">{latest.regime ?? "Regime desconhecido"}</p>
                <div className="grid grid-cols-4 gap-1 mt-2">
                  {[
                    { l: "Padrão",   v: latest.pattern_score },
                    { l: "Regime",   v: latest.regime_score },
                    { l: "Contexto", v: latest.context_score_comp },
                    { l: "Conflu.",  v: latest.confluence_score },
                  ].map(({ l, v }) => (
                    <div key={l} className="text-center">
                      <p className="text-[10px] text-[#6b7280]">{l}</p>
                      <p className="text-xs font-semibold text-amber-400">{(v ?? 0).toFixed(1)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Média */}
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="text-xs text-[#6b7280]">Média últimos {entries.length} setups</span>
            <span className="text-xs font-bold text-amber-400">{avgScore.toFixed(1)}</span>
          </div>

          {/* Mini-histórico */}
          <div className="space-y-1 max-h-[200px] overflow-y-auto">
            {entries.slice(0, 15).map((e) => (
              <div
                key={e.id}
                className="flex items-center gap-2 text-xs py-1 border-b border-[#1f2937] last:border-0"
              >
                <span className="text-[10px] text-[#6b7280] w-12 shrink-0">
                  {new Date(e.computed_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-[#9ca3af] w-20 truncate">{e.symbol}</span>
                <span className={`w-10 text-center font-mono text-[10px] px-1 rounded ${
                  e.signal === "BUY" ? "bg-emerald-500/10 text-emerald-400" :
                  e.signal === "SELL" ? "bg-red-500/10 text-red-400" : "text-[#6b7280]"
                }`}>{e.signal ?? "—"}</span>
                <div className="flex-1 h-1 bg-[#1f2937] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${e.quality_score}%`,
                      background: e.quality_score >= 60 ? "#f59e0b" : "#6b7280",
                    }}
                  />
                </div>
                <span className="w-10 text-right font-semibold text-amber-400">
                  {e.quality_score.toFixed(0)}
                </span>
                {e.outcome && (
                  <span className={`text-[10px] ${e.outcome === "WIN" ? "text-emerald-400" : e.outcome === "LOSS" ? "text-red-400" : "text-[#6b7280]"}`}>
                    {e.outcome}
                  </span>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
