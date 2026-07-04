/**
 * TradeAI - Componente: Market Analysis (Fase 3)
 * Exibe o resumo qualitativo: Trend, Momentum, Volatility.
 */

"use client";

import type { AnalysisData, TrendLabel, MomentumLabel, VolatilityLabel } from "@/types";
import { clsx } from "clsx";

// ── Mapeamentos de cor e ícone ────────────────────────────────────────────────

const TREND_CONFIG: Record<TrendLabel, { color: string; bg: string; icon: string }> = {
  "Strong Bullish": { color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20", icon: "↑↑" },
  "Bullish":        { color: "text-green-400",   bg: "bg-green-500/10 border-green-500/20",   icon: "↑"  },
  "Sideways":       { color: "text-amber-400",   bg: "bg-amber-500/10 border-amber-500/20",   icon: "→"  },
  "Bearish":        { color: "text-orange-400",  bg: "bg-orange-500/10 border-orange-500/20", icon: "↓"  },
  "Strong Bearish": { color: "text-red-400",     bg: "bg-red-500/10 border-red-500/20",       icon: "↓↓" },
};

const MOMENTUM_CONFIG: Record<MomentumLabel, { color: string; label: string }> = {
  "Strong":  { color: "text-green-400",  label: "Forte"   },
  "Neutral": { color: "text-amber-400",  label: "Neutro"  },
  "Weak":    { color: "text-red-400",    label: "Fraco"   },
};

const VOLATILITY_CONFIG: Record<VolatilityLabel, { color: string; label: string; desc: string }> = {
  "Low":    { color: "text-blue-400",  label: "Baixa",  desc: "ATR < 0.8% do preço" },
  "Medium": { color: "text-amber-400", label: "Média",  desc: "ATR 0.8–2.5% do preço" },
  "High":   { color: "text-red-400",   label: "Alta",   desc: "ATR > 2.5% do preço" },
};

// ── Componente ────────────────────────────────────────────────────────────────

interface MarketAnalysisProps {
  analysis: AnalysisData | null;
  loading:  boolean;
  symbol:   string;
}

export function MarketAnalysis({ analysis, loading, symbol }: MarketAnalysisProps) {
  const a = analysis;

  const trendCfg = a ? TREND_CONFIG[a.trend] : null;
  const momCfg   = a ? MOMENTUM_CONFIG[a.momentum] : null;
  const volCfg   = a ? VOLATILITY_CONFIG[a.volatility] : null;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Market Analysis</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {symbol.replace("USDT", "")}/USDT · Análise técnica objetiva
          </p>
        </div>
        {loading && (
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {!a && !loading && (
        <p className="text-xs text-[#6b7280] text-center py-6">
          Aguardando análise...
        </p>
      )}

      {a && trendCfg && momCfg && volCfg && (
        <div className="flex flex-col gap-3">

          {/* Trend */}
          <div className={clsx("rounded-lg border px-4 py-3", trendCfg.bg)}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#6b7280] mb-0.5">Tendência</p>
                <p className={clsx("text-base font-bold", trendCfg.color)}>
                  {a.trend}
                </p>
              </div>
              <span className={clsx("text-2xl font-black", trendCfg.color)}>
                {trendCfg.icon}
              </span>
            </div>
            <p className="text-xs text-[#4b5563] mt-1">Alinhamento das EMAs 9/21/50/200</p>
          </div>

          {/* Momentum */}
          <div className="rounded-lg border border-[#1f2937] bg-[#0f1623] px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#6b7280] mb-0.5">Momentum</p>
                <p className={clsx("text-base font-bold", momCfg.color)}>{momCfg.label}</p>
              </div>
              <span className="text-xs text-[#4b5563]">RSI + MACD</span>
            </div>
          </div>

          {/* Volatility */}
          <div className="rounded-lg border border-[#1f2937] bg-[#0f1623] px-4 py-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-[#6b7280] mb-0.5">Volatilidade</p>
                <p className={clsx("text-base font-bold", volCfg.color)}>{volCfg.label}</p>
              </div>
              <span className="text-xs text-[#4b5563]">{volCfg.desc}</span>
            </div>
          </div>

        </div>
      )}

      {/* Footer */}
      <div className="pt-1 border-t border-[#1f2937]">
        <p className="text-xs text-[#4b5563]">
          Fase 4+: integrar análise de notícias e sentimento
        </p>
      </div>
    </div>
  );
}
