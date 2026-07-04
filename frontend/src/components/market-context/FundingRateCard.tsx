"use client";

import type { FundingRateData } from "@/types";

interface Props {
  rates:   FundingRateData[];
  loading?: boolean;
}

const SENTIMENT_STYLE = {
  BULLISH: { text: "text-emerald-400", bg: "bg-emerald-500/10", border: "border-emerald-500/20" },
  NEUTRAL: { text: "text-[#9ca3af]",  bg: "bg-[#1f2937]",      border: "border-[#374151]" },
  BEARISH: { text: "text-red-400",    bg: "bg-red-500/10",      border: "border-red-500/20" },
};

function SymbolRow({ rate }: { rate: FundingRateData }) {
  const style = SENTIMENT_STYLE[rate.sentiment];
  const symbol = rate.symbol.replace("USDT", "");
  const isPos  = rate.rate_percent >= 0;

  return (
    <div className="flex items-center justify-between py-2.5 border-b border-[#1f2937] last:border-0">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold text-[#f9fafb] w-8">{symbol}</span>
        <span className={`text-[10px] px-1.5 py-0.5 rounded border ${style.bg} ${style.text} ${style.border}`}>
          {rate.sentiment}
        </span>
      </div>
      <div className="text-right">
        <p className={`text-sm font-semibold ${isPos ? "text-emerald-400" : "text-red-400"}`}>
          {isPos ? "+" : ""}{rate.rate_percent.toFixed(4)}%
        </p>
        <p className="text-[10px] text-[#4b5563]">
          {new Date(rate.timestamp * 1000).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
    </div>
  );
}

export function FundingRateCard({ rates, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Funding Rate</h3>
        <span className="text-xs text-[#4b5563]">Binance Futures</span>
      </div>

      {loading ? (
        <div className="h-28 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : rates.length === 0 ? (
        <div className="h-28 flex items-center justify-center">
          <p className="text-xs text-[#4b5563]">Aguardando dados...</p>
        </div>
      ) : (
        <div>
          {rates.map((r) => <SymbolRow key={r.id} rate={r} />)}
          <p className="text-[10px] text-[#4b5563] mt-2">
            Positivo = longs pagam shorts (otimismo)
          </p>
        </div>
      )}
    </div>
  );
}
