/**
 * TradeAI - Componente: Market Panel
 * Exibe preço atual, variação 24h, volume, máxima e mínima do ativo selecionado.
 * O preço em tempo real vem via WebSocket; as demais estatísticas via REST (30s).
 */

"use client";

import { clsx } from "clsx";
import type { MarketStatsResponse, WsPriceUpdate } from "@/types";

interface MarketPanelProps {
  symbol: string;
  stats: MarketStatsResponse | null;
  livePrice?: WsPriceUpdate;
  loading?: boolean;
}

function fmt(value: number | undefined, decimals = 2): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function fmtVolume(value: number | undefined): string {
  if (!value) return "—";
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000)     return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000)         return `${(value / 1_000).toFixed(2)}K`;
  return fmt(value);
}

export function MarketPanel({ symbol, stats, livePrice, loading }: MarketPanelProps) {
  // Preço preferencial: WebSocket (tempo real) > REST (banco)
  const currentPrice = livePrice?.price ?? stats?.price;
  const change24h    = stats?.change_24h;
  const isPositive   = (change24h ?? 0) >= 0;

  const items = [
    {
      label: "Volume 24h",
      value: fmtVolume(stats?.volume_24h),
      sub: symbol.replace("USDT", ""),
    },
    {
      label: "Máxima 24h",
      value: stats?.high_24h ? `$${fmt(stats.high_24h)}` : "—",
      sub: "USDT",
    },
    {
      label: "Mínima 24h",
      value: stats?.low_24h ? `$${fmt(stats.low_24h)}` : "—",
      sub: "USDT",
    },
  ];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex flex-col sm:flex-row sm:items-center gap-6">

        {/* Preço principal */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-medium text-[#9ca3af] uppercase tracking-wider">
              {symbol.replace("USDT", "")}
              <span className="text-[#4b5563]">/USDT</span>
            </span>
            {/* Indicador live */}
            {livePrice && (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live
              </span>
            )}
          </div>

          <div className="flex items-baseline gap-3">
            <span
              className={clsx(
                "text-3xl font-bold font-mono tabular-nums",
                loading ? "text-[#6b7280]" : "text-[#f9fafb]"
              )}
            >
              {loading ? "Carregando..." : currentPrice ? `$${fmt(currentPrice)}` : "—"}
            </span>

            {change24h !== undefined && (
              <span
                className={clsx(
                  "text-base font-semibold font-mono",
                  isPositive ? "text-emerald-400" : "text-red-400"
                )}
              >
                {isPositive ? "▲" : "▼"} {Math.abs(change24h).toFixed(2)}%
              </span>
            )}
          </div>
        </div>

        {/* Estatísticas 24h */}
        <div className="flex flex-wrap gap-4 sm:gap-6">
          {items.map((item) => (
            <div key={item.label} className="min-w-[90px]">
              <p className="text-xs text-[#6b7280] mb-0.5">{item.label}</p>
              <p className="text-sm font-mono font-semibold text-[#f9fafb]">
                {loading ? "—" : item.value}
              </p>
              <p className="text-xs text-[#4b5563]">{item.sub}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
