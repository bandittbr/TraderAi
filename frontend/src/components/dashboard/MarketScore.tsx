/**
 * TradeAI - Componente: Market Score V2 (Fase 3)
 * Score 0–100 com breakdown: Trend | Momentum | Volume | Volatility.
 * Usa dados de MarketStatsResponse (score total + breakdown por dimensão).
 */

"use client";

import { clsx } from "clsx";
import type { MarketStatsResponse } from "@/types";

// ── Configuração por faixa de score ──────────────────────────────────────────

function getScoreConfig(score: number) {
  if (score >= 75) return { label: "Forte",    color: "text-emerald-400", barColor: "bg-emerald-400" };
  if (score >= 55) return { label: "Moderado", color: "text-blue-400",    barColor: "bg-blue-400"    };
  if (score >= 35) return { label: "Neutro",   color: "text-amber-400",   barColor: "bg-amber-400"   };
  return              { label: "Fraco",    color: "text-red-400",     barColor: "bg-red-400"     };
}

// ── Sub-barra de dimensão ─────────────────────────────────────────────────────

function DimensionBar({
  label, value, max, color,
}: {
  label: string;
  value: number;
  max:   number;
  color: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-[#4b5563] w-20 shrink-0">{label}</span>
      <div className="flex-1 h-1 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-700", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] text-[#6b7280] w-6 text-right tabular-nums">
        {value.toFixed(0)}
      </span>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

interface MarketScoreProps {
  stats:   MarketStatsResponse | null;
  symbol?: string;
  loading?: boolean;
}

export function MarketScore({ stats, symbol = "BTCUSDT", loading }: MarketScoreProps) {
  const isLoading    = loading || stats === null;
  const totalScore   = stats?.market_score ?? 50;
  const config       = getScoreConfig(totalScore);

  const trendScore   = stats?.trend_score      ?? 0;
  const momentumScore = stats?.momentum_score  ?? 0;
  const volumeScore  = stats?.volume_score     ?? 0;
  const volatilityScore = stats?.volatility_score ?? 0;
  const hasBreakdown = !isLoading && (trendScore + momentumScore + volumeScore + volatilityScore) > 0;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-3 h-full">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[#9ca3af] uppercase tracking-wider">
          Market Score
        </span>
        <span className="text-xs text-[#6b7280]">
          {symbol.replace("USDT", "")}/USDT
        </span>
      </div>

      {/* Score principal */}
      <div className="flex items-center gap-3">
        <span className={clsx(
          "text-4xl font-bold font-mono tabular-nums leading-none",
          isLoading ? "text-[#6b7280]" : config.color,
        )}>
          {isLoading ? "—" : totalScore}
        </span>
        <div className="flex flex-col">
          <span className="text-xs text-[#6b7280]">de 100</span>
          {!isLoading && (
            <span className={clsx("text-xs font-semibold", config.color)}>
              {config.label}
            </span>
          )}
        </div>
      </div>

      {/* Barra total */}
      <div className="w-full h-2 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className={clsx(
            "h-full rounded-full transition-all duration-700",
            isLoading ? "bg-[#374151]" : config.barColor,
          )}
          style={{ width: isLoading ? "0%" : `${totalScore}%` }}
        />
      </div>

      {/* Breakdown V2 */}
      <div className="flex flex-col gap-1.5 pt-1 border-t border-[#1f2937]">
        <p className="text-[10px] text-[#4b5563] uppercase tracking-wider mb-0.5">Breakdown</p>
        <DimensionBar label="Tendência"   value={hasBreakdown ? trendScore    : 0} max={35} color="bg-blue-500"    />
        <DimensionBar label="Momentum"    value={hasBreakdown ? momentumScore : 0} max={25} color="bg-purple-500"  />
        <DimensionBar label="Volume"      value={hasBreakdown ? volumeScore   : 0} max={25} color="bg-amber-500"   />
        <DimensionBar label="Volatilidade" value={hasBreakdown ? volatilityScore : 0} max={15} color="bg-rose-500" />
      </div>

      {/* Fase futura */}
      <p className="text-[10px] text-[#374151]">
        + Notícias · Sentimento · IA → Fase 4+
      </p>
    </div>
  );
}
