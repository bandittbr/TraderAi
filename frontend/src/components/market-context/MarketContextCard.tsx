"use client";

import type { ContextScoreData } from "@/types";

interface Props {
  data:    ContextScoreData | null;
  loading?: boolean;
}

const LABEL_STYLE = {
  Bullish: "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
  Neutral: "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
  Bearish: "text-red-400 border-red-500/30 bg-red-500/10",
};

function ScoreBar({
  label, value, color,
}: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-[#6b7280]">{label}</span>
        <span className="text-xs font-semibold text-[#9ca3af]">{value.toFixed(0)}</span>
      </div>
      <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
}

export function MarketContextCard({ data, loading }: Props) {
  const label = (data?.context_label ?? "Neutral") as "Bullish" | "Neutral" | "Bearish";

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Market Context</h3>
        <span className="text-xs text-[#4b5563]">Score 0-100</span>
      </div>

      {loading || !data ? (
        <div className="h-48 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Score principal */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-3xl font-bold text-[#f9fafb]">
                {data.context_score.toFixed(0)}
              </p>
              <p className="text-xs text-[#6b7280] mt-0.5">Context Score</p>
            </div>
            <span className={`text-sm font-semibold px-3 py-1 rounded-full border ${
              LABEL_STYLE[label]
            }`}>
              {data.context_label}
            </span>
          </div>

          {/* Barras de dimensão */}
          <div className="space-y-2.5">
            <ScoreBar
              label="Fear &amp; Greed"
              value={data.fear_greed}
              color={data.fear_greed >= 55 ? "bg-emerald-500" : data.fear_greed <= 45 ? "bg-red-500" : "bg-yellow-500"}
            />
            <ScoreBar
              label="Notícias"
              value={data.news_score}
              color={data.news_score >= 60 ? "bg-emerald-500" : data.news_score <= 40 ? "bg-red-500" : "bg-yellow-500"}
            />
            <ScoreBar
              label="Funding"
              value={data.funding_score}
              color={data.funding_score >= 60 ? "bg-emerald-500" : data.funding_score <= 40 ? "bg-red-500" : "bg-yellow-500"}
            />
            <ScoreBar
              label="Open Interest"
              value={data.oi_score}
              color="bg-blue-500"
            />
          </div>

          {/* Resumo notícias */}
          <div className="flex gap-2 pt-1 border-t border-[#1f2937]">
            <div className="flex-1 text-center">
              <p className="text-sm font-semibold text-emerald-400">{data.news_sentiment.positive}</p>
              <p className="text-[10px] text-[#4b5563]">Positivas</p>
            </div>
            <div className="flex-1 text-center">
              <p className="text-sm font-semibold text-[#9ca3af]">{data.news_sentiment.neutral}</p>
              <p className="text-[10px] text-[#4b5563]">Neutras</p>
            </div>
            <div className="flex-1 text-center">
              <p className="text-sm font-semibold text-red-400">{data.news_sentiment.negative}</p>
              <p className="text-[10px] text-[#4b5563]">Negativas</p>
            </div>
            <div className="flex-1 text-center">
              <p className="text-sm font-semibold text-[#f9fafb]">{data.news_sentiment.total}</p>
              <p className="text-[10px] text-[#4b5563]">Total (24h)</p>
            </div>
          </div>

          {data.oi_change_pct !== null && (
            <p className="text-[10px] text-[#4b5563]">
              OI change: {data.oi_change_pct >= 0 ? "+" : ""}{data.oi_change_pct?.toFixed(2)}%
            </p>
          )}
        </div>
      )}
    </div>
  );
}
