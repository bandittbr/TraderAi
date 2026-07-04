"use client";

import type { OpenInterestData } from "@/types";

interface Props {
  data:    OpenInterestData[];
  loading?: boolean;
}

function formatUSD(value: number): string {
  if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  return `$${value.toFixed(0)}`;
}

function OIRow({ oi }: { oi: OpenInterestData }) {
  const symbol = oi.symbol.replace("USDT", "");
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-[#1f2937] last:border-0">
      <span className="text-sm font-semibold text-[#f9fafb] w-8">{symbol}</span>
      <div className="text-right">
        <p className="text-sm font-semibold text-[#f9fafb]">
          {formatUSD(oi.open_interest_usd)}
        </p>
        <p className="text-[10px] text-[#4b5563]">
          {oi.open_interest.toLocaleString("en-US", { maximumFractionDigits: 2 })} contratos
        </p>
      </div>
    </div>
  );
}

export function OpenInterestCard({ data, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Open Interest</h3>
        <span className="text-xs text-[#4b5563]">Binance Futures</span>
      </div>

      {loading ? (
        <div className="h-28 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data.length === 0 ? (
        <div className="h-28 flex items-center justify-center">
          <p className="text-xs text-[#4b5563]">Aguardando dados...</p>
        </div>
      ) : (
        <div>
          {data.map((oi) => <OIRow key={oi.id} oi={oi} />)}
          <p className="text-[10px] text-[#4b5563] mt-2">
            OI crescente + preço subindo = tendência forte
          </p>
        </div>
      )}
    </div>
  );
}
