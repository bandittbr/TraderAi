"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface CombinationStats {
  criteria: string[];
  criteria_key: string;
  sample_size: number;
  wins: number;
  losses: number;
  win_rate: number;
  profit_factor: number;
  expectancy: number;
  max_drawdown: number;
  score: number;
}

interface CombinationReport {
  top_all: CombinationStats[];
  analyzed: number;
  valid: number;
}

const CRITERION_LABELS: Record<string, string> = {
  ema_cross: "EMA×",
  ema_macro: "EMAm",
  ema_price: "EMAp",
  macd_trend: "MACD",
  macd_signal: "MACDs",
  rsi: "RSI",
  structure: "STR",
  bos: "BOS",
  sr_zone: "S/R",
  sweep: "SWP",
  fvg: "FVG",
  hvn_lvn: "VOL",
  liquidity: "LIQ",
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, score * 20);
  const color = pct > 60 ? "bg-emerald-500" : pct > 30 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="w-full bg-[#0a0e1a] rounded-full h-1 mt-1">
      <div className={`h-1 rounded-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function CombinationRanking() {
  const [data, setData] = useState<CombinationReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"all" | "top10">("all");

  async function load() {
    try {
      const r = await fetch(`${API_BASE}/optimizer/combinations?lookback_days=90&top_n=50`);
      if (r.ok) setData(await r.json());
    } catch (_) {}
    setLoading(false);
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const items = view === "top10"
    ? (data?.top_all ?? []).slice(0, 10)
    : (data?.top_all ?? []);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Combinações Lucrativas</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {data ? `${data.valid} válidas · ${data.analyzed} analisadas` : "—"}
          </p>
        </div>
        <div className="flex gap-1">
          {(["all", "top10"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`text-[10px] px-2 py-0.5 rounded transition-colors ${
                view === v ? "bg-purple-500/30 text-purple-300" : "text-[#6b7280] hover:text-[#9ca3af]"
              }`}
            >
              {v === "top10" ? "Top 10" : "Todas"}
            </button>
          ))}
        </div>
      </div>

      {loading && <p className="text-xs text-[#6b7280] text-center py-4">Carregando…</p>}

      {!loading && items.length === 0 && (
        <p className="text-xs text-[#6b7280] text-center py-4">
          Acumulando histórico…
        </p>
      )}

      {!loading && items.length > 0 && (
        <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
          {items.map((c, idx) => (
            <div key={c.criteria_key} className="bg-[#0f1623] rounded-lg p-2.5">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] text-[#4b5563] font-mono w-4">#{idx + 1}</span>
                    {c.criteria.map((cr) => (
                      <span
                        key={cr}
                        className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-300 font-mono"
                      >
                        {CRITERION_LABELS[cr] ?? cr}
                      </span>
                    ))}
                  </div>
                  <ScoreBar score={c.score} />
                </div>
                <div className="flex items-center gap-2 text-right shrink-0">
                  <div>
                    <p className="text-[9px] text-[#6b7280]">WR</p>
                    <p className={`text-xs font-semibold ${c.win_rate >= 50 ? "text-emerald-400" : "text-red-400"}`}>
                      {c.win_rate.toFixed(0)}%
                    </p>
                  </div>
                  <div>
                    <p className="text-[9px] text-[#6b7280]">PF</p>
                    <p className={`text-xs font-semibold ${c.profit_factor >= 1 ? "text-emerald-400" : "text-red-400"}`}>
                      {c.profit_factor.toFixed(2)}
                    </p>
                  </div>
                  <div>
                    <p className="text-[9px] text-[#6b7280]">N</p>
                    <p className="text-xs text-[#9ca3af]">{c.sample_size}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
