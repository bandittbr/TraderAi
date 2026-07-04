/**
 * TradeAI - Componente: Technical Indicators (Fase 3)
 * Exibe RSI, EMAs, MACD e ATR calculados pelo backend.
 * Atualização automática via hook useIndicators (polling 60s).
 */

"use client";

import type { IndicatorData } from "@/types";
import { clsx } from "clsx";

// ── Utilitários de formatação ─────────────────────────────────────────────────

function fmt(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined) return "—";
  if (Math.abs(value) >= 1000) return value.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
  return value.toFixed(decimals);
}

function fmtPrice(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (v >= 1000) return v.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return v.toFixed(4);
}

// ── Sub-componentes ───────────────────────────────────────────────────────────

function IndicatorRow({
  label, value, sublabel, color,
}: {
  label: string;
  value: string;
  sublabel?: string;
  color?: string;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#1f2937] last:border-0">
      <div>
        <span className="text-xs font-medium text-[#9ca3af]">{label}</span>
        {sublabel && <span className="ml-2 text-xs text-[#4b5563]">{sublabel}</span>}
      </div>
      <span className={clsx("text-sm font-mono font-semibold tabular-nums", color ?? "text-[#f9fafb]")}>
        {value}
      </span>
    </div>
  );
}

function RSIBar({ rsi }: { rsi: number | null }) {
  if (rsi === null) return null;

  let color = "text-[#9ca3af]";
  let label = "Neutro";

  if (rsi >= 70) { color = "text-red-400";   label = "Sobrecomprado"; }
  else if (rsi >= 55) { color = "text-green-400"; label = "Forte"; }
  else if (rsi <= 30) { color = "text-blue-400";  label = "Sobrevendido"; }
  else if (rsi <= 45) { color = "text-amber-400"; label = "Fraco"; }

  const pct = Math.max(0, Math.min(100, rsi));

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs text-[#6b7280]">RSI 14</span>
        <span className={clsx("text-xs font-semibold", color)}>{rsi.toFixed(1)} · {label}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#1f2937] overflow-hidden">
        <div
          className={clsx("h-full rounded-full transition-all duration-500",
            rsi >= 70 ? "bg-red-500" : rsi >= 55 ? "bg-green-500" : rsi <= 30 ? "bg-blue-500" : rsi <= 45 ? "bg-amber-500" : "bg-gray-500"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-[#4b5563] mt-0.5">
        <span>30</span><span>50</span><span>70</span>
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────

interface TechnicalIndicatorsProps {
  indicators: IndicatorData | null;
  loading:    boolean;
  symbol:     string;
}

export function TechnicalIndicators({ indicators, loading, symbol }: TechnicalIndicatorsProps) {
  const ind = indicators;

  // Direção do MACD
  const macdColor = ind?.macd !== null && ind?.macd !== undefined
    ? ind.macd > 0 ? "text-green-400" : "text-red-400"
    : undefined;

  const histColor = ind?.macd_histogram !== null && ind?.macd_histogram !== undefined
    ? ind.macd_histogram > 0 ? "text-green-400" : "text-red-400"
    : undefined;

  // Alinhamento de EMAs
  const emaAligned =
    ind?.ema_9  !== null && ind?.ema_21 !== null &&
    ind?.ema_21 !== null && ind?.ema_50 !== null &&
    ind?.ema_9  !== undefined && ind?.ema_21 !== undefined &&
    ind?.ema_50 !== undefined;

  const emaBullish = emaAligned &&
    (ind!.ema_9! > ind!.ema_21!) && (ind!.ema_21! > ind!.ema_50!);

  const emaBearish = emaAligned &&
    (ind!.ema_9! < ind!.ema_21!) && (ind!.ema_21! < ind!.ema_50!);

  const emaStatusColor = emaBullish ? "text-green-400" : emaBearish ? "text-red-400" : "text-amber-400";
  const emaStatus      = emaBullish ? "Alinhadas ↑" : emaBearish ? "Alinhadas ↓" : "Mistas";

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Technical Indicators</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {symbol.replace("USDT", "")}/USDT · Timeframe 1h · Atualização a cada 60s
          </p>
        </div>
        {loading && (
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {!ind && !loading && (
        <p className="text-xs text-[#6b7280] text-center py-4">
          Aguardando cálculo de indicadores...
        </p>
      )}

      {ind && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {/* ── RSI ─────────────────────────────────────────── */}
          <div>
            <h4 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider mb-3">
              Momentum · RSI
            </h4>
            <RSIBar rsi={ind.rsi} />
            <IndicatorRow
              label="ATR 14"
              value={fmtPrice(ind.atr)}
              sublabel="volatilidade"
            />
          </div>

          {/* ── EMAs ─────────────────────────────────────────── */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider">
                Médias Móveis · EMA
              </h4>
              <span className={clsx("text-xs font-medium", emaStatusColor)}>{emaStatus}</span>
            </div>
            <IndicatorRow label="EMA 9"   value={fmtPrice(ind.ema_9)}   color="text-purple-400" />
            <IndicatorRow label="EMA 21"  value={fmtPrice(ind.ema_21)}  color="text-blue-400"   />
            <IndicatorRow label="EMA 50"  value={fmtPrice(ind.ema_50)}  color="text-amber-400"  />
            <IndicatorRow label="EMA 200" value={fmtPrice(ind.ema_200)} color="text-red-400"    />
          </div>

          {/* ── MACD ─────────────────────────────────────────── */}
          <div>
            <h4 className="text-xs font-semibold text-[#6b7280] uppercase tracking-wider mb-3">
              MACD (12/26/9)
            </h4>
            <IndicatorRow label="MACD"      value={fmt(ind.macd, 2)}           color={macdColor} />
            <IndicatorRow label="Signal"    value={fmt(ind.macd_signal, 2)}    />
            <IndicatorRow label="Histogram" value={fmt(ind.macd_histogram, 2)} color={histColor} />
            <div className="mt-2 pt-2 border-t border-[#1f2937]">
              <div className="flex items-center gap-2">
                <div className={clsx("w-2 h-2 rounded-full",
                  ind.macd_histogram !== null && ind.macd_histogram !== undefined
                    ? ind.macd_histogram > 0 ? "bg-green-500" : "bg-red-500"
                    : "bg-gray-500"
                )} />
                <span className="text-xs text-[#6b7280]">
                  {ind.macd !== null && ind.macd !== undefined
                    ? ind.macd > 0 ? "Momentum bullish" : "Momentum bearish"
                    : "Aguardando dados"}
                </span>
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
