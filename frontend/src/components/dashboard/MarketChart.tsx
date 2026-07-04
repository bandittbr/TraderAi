/**
 * TradeAI - Componente: Market Chart
 * Gráfico de candlestick em tempo real usando TradingView lightweight-charts v4.
 * Suporta troca de timeframe: 15m | 30m | 45m | 1h.
 * Atualiza o último candle automaticamente via WebSocket.
 *
 * Renderização client-side obrigatória (SSR desativado via "use client").
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
// useCallback mantido para loadCandles; useState mantido para timeframe e loading
import { createChart, ColorType } from "lightweight-charts";
import type { IChartApi, ISeriesApi, CandlestickData, UTCTimestamp } from "lightweight-charts";
import { getCandles } from "@/lib/api";
import type { CandleData, WsPriceUpdate } from "@/types";
import { clsx } from "clsx";

// Duração de cada timeframe em segundos
const TF_SECONDS: Record<string, number> = {
  "15m": 900,
  "30m": 1800,
  "45m": 2700,
  "1h":  3600,
};

// ── Configuração ──────────────────────────────────────────────────────────────

const TIMEFRAMES = [
  { label: "15m", value: "15m" },
  { label: "30m", value: "30m" },
  { label: "45m", value: "45m" },
  { label: "1h",  value: "1h"  },
];

const CHART_COLORS = {
  background:  "#0a0e1a",
  text:        "#9ca3af",
  grid:        "#1f2937",
  border:      "#1f2937",
  upColor:     "#10b981",
  downColor:   "#ef4444",
};

// ── Conversão ─────────────────────────────────────────────────────────────────

/**
 * Converte CandleData para o formato CandlestickData do lightweight-charts.
 * Number() garante que o time seja sempre um primitivo numérico — nunca um objeto.
 */
function toChartCandle(c: CandleData): CandlestickData {
  return {
    time:  Number(c.time) as UTCTimestamp,
    open:  Number(c.open),
    high:  Number(c.high),
    low:   Number(c.low),
    close: Number(c.close),
  };
}

// ── Componente ────────────────────────────────────────────────────────────────

interface MarketChartProps {
  symbol: string;
  livePrice?: WsPriceUpdate;
}

export function MarketChart({ symbol, livePrice }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef     = useRef<IChartApi | null>(null);
  const seriesRef    = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [timeframe, setTimeframe] = useState("1h");
  const [loading,   setLoading]   = useState(true);

  /**
   * Refs em vez de state para evitar stale closure no efeito do WebSocket.
   * lastSeriesTimeRef → epoch seconds do último candle enviado ao lightweight-charts.
   * lastCandleRef     → snapshot OHLCV do último candle (para calcular high/low acumulado).
   */
  const lastSeriesTimeRef = useRef<number>(0);
  const lastCandleRef     = useRef<CandleData | null>(null);

  // ── Inicialização do chart ────────────────────────────────────────────────

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: CHART_COLORS.background },
        textColor:  CHART_COLORS.text,
      },
      grid: {
        vertLines: { color: CHART_COLORS.grid },
        horzLines: { color: CHART_COLORS.grid },
      },
      timeScale: {
        borderColor:  CHART_COLORS.border,
        timeVisible:  true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: CHART_COLORS.border,
      },
      crosshair: {
        vertLine: { labelBackgroundColor: "#374151" },
        horzLine: { labelBackgroundColor: "#374151" },
      },
      width:  containerRef.current.clientWidth,
      height: 360,
    });

    const series = chart.addCandlestickSeries({
      upColor:        CHART_COLORS.upColor,
      downColor:      CHART_COLORS.downColor,
      borderUpColor:  CHART_COLORS.upColor,
      borderDownColor: CHART_COLORS.downColor,
      wickUpColor:    CHART_COLORS.upColor,
      wickDownColor:  CHART_COLORS.downColor,
    });

    chartRef.current  = chart;
    seriesRef.current = series;

    // Responsividade
    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current  = null;
      seriesRef.current = null;
    };
  }, []);

  // ── Carregamento de candles ───────────────────────────────────────────────

  const loadCandles = useCallback(async () => {
    if (!seriesRef.current) return;
    setLoading(true);

    // Reseta os refs antes de carregar novo conjunto de candles
    lastSeriesTimeRef.current = 0;
    lastCandleRef.current     = null;

    const candles = await getCandles(symbol, timeframe, 150);

    if (seriesRef.current && candles.length > 0) {
      seriesRef.current.setData(candles.map(toChartCandle));

      const last = candles[candles.length - 1];
      lastCandleRef.current     = last;
      lastSeriesTimeRef.current = Number(last.time);   // registra o tempo do último candle no chart

      chartRef.current?.timeScale().fitContent();
    }

    setLoading(false);
  }, [symbol, timeframe]);

  // Recarrega ao trocar símbolo ou timeframe
  useEffect(() => {
    loadCandles();
  }, [loadCandles]);

  // ── Atualização em tempo real via WebSocket ───────────────────────────────

  useEffect(() => {
    if (!livePrice || !seriesRef.current) return;
    if (livePrice.symbol !== symbol) return;

    // Snapshot local das refs — garante narrowing correto de tipos pelo TypeScript
    const lastSeriesTime = lastSeriesTimeRef.current;
    const lastCandle     = lastCandleRef.current;

    // Série ainda não foi populada via REST — aguarda loadCandles completar
    if (lastSeriesTime === 0 || !lastCandle) return;

    const intervalSec = TF_SECONDS[timeframe] ?? 3600;

    // Garante que timestamp WS seja número primitivo antes de qualquer cálculo
    const priceTimeSec = Math.floor(Number(livePrice.timestamp) / 1000);
    const candleStart  = Math.floor(priceTimeSec / intervalSec) * intervalSec;

    // ── Proteção 1: timestamp inválido ──────────────────────────────────────
    if (!Number.isFinite(candleStart) || candleStart <= 0) {
      console.warn(`[MarketChart] Timestamp WS inválido descartado: ${livePrice.timestamp}`);
      return;
    }

    // ── Proteção 2: candle fora de ordem ────────────────────────────────────
    // lightweight-charts lança "Cannot update oldest data" se candleStart < último time da série.
    if (candleStart < lastSeriesTime) {
      console.warn(
        `[MarketChart] Candle WS desatualizado descartado — ` +
        `candleStart=${candleStart} < lastSeriesTime=${lastSeriesTime}`,
      );
      return;
    }

    const isCurrentBar  = candleStart === lastSeriesTime;

    const updatedCandle: CandlestickData = {
      time:  candleStart as UTCTimestamp,
      // Se ainda no mesmo período: acumula high/low; se novo período: usa valores do tick
      open:  isCurrentBar ? lastCandle.open  : livePrice.open,
      high:  isCurrentBar ? Math.max(lastCandle.high, livePrice.price) : livePrice.price,
      low:   isCurrentBar ? Math.min(lastCandle.low,  livePrice.price) : livePrice.price,
      close: livePrice.price,
    };

    try {
      seriesRef.current.update(updatedCandle);

      // Atualiza refs com os valores mais recentes
      lastSeriesTimeRef.current = candleStart;
      lastCandleRef.current = {
        time:   candleStart,
        open:   updatedCandle.open,
        high:   updatedCandle.high,
        low:    updatedCandle.low,
        close:  updatedCandle.close,
        volume: lastCandle.volume,
      };
    } catch (err) {
      // Nunca deve chegar aqui após as proteções acima — mas captura por segurança
      console.warn(`[MarketChart] Erro inesperado em series.update(): ${err}`);
    }
  }, [livePrice, symbol, timeframe]); // lastCandle removido — usa ref para evitar stale closure

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">
            {symbol.replace("USDT", "")}/USDT
          </h3>
          <p className="text-xs text-[#6b7280] mt-0.5">Candles · Binance</p>
        </div>

        {/* Seletor de timeframe */}
        <div className="flex gap-1">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf.value}
              onClick={() => setTimeframe(tf.value)}
              className={clsx(
                "px-2.5 py-1 text-xs rounded-md font-medium transition-colors",
                timeframe === tf.value
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "bg-[#1f2937] text-[#9ca3af] hover:text-[#f9fafb] border border-transparent"
              )}
            >
              {tf.label}
            </button>
          ))}
        </div>
      </div>

      {/* Container do chart */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/80 rounded-lg z-10">
            <div className="flex flex-col items-center gap-2">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[#6b7280]">Carregando candles...</span>
            </div>
          </div>
        )}
        <div ref={containerRef} className="w-full" />
      </div>

      {/* Rodapé */}
      <div className="flex items-center justify-between pt-1 border-t border-[#1f2937]">
        <span className="text-xs text-[#4b5563]">
          Timeframe: <span className="text-[#6b7280]">{timeframe}</span>
        </span>
        <span className="text-xs text-[#4b5563]">
          Fase 3+: múltiplos ativos simultâneos
        </span>
      </div>
    </div>
  );
}
