/**
 * TradeAI - AgentChart Component
 * Gráfico TradingView com markers de compra/venda de um agente específico.
 * Mostra candles + markers de abertura (seta) e fechamento (pnl badge).
 * Atualiza em tempo real via WebSocket.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createChart, ColorType, CrosshairMode } from "lightweight-charts";
import type {
  IChartApi,
  ISeriesApi,
  CandlestickData,
  UTCTimestamp,
  Time,
} from "lightweight-charts";
import { clsx } from "clsx";

// ── Types ────────────────────────────────────────────────────────────────────

interface TradeMarker {
  trade_id: number;
  open_time: number;      // epoch seconds
  open_price: number;
  side: string;           // "LONG" | "SHORT"
  confidence?: number;
  close_time: number | null;
  close_price: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  reason: string | null;
  is_open: boolean;
}

interface AgentChartProps {
  agent: string;           // "paper" | "scalper" | "worker"
  symbol: string;
  livePrice?: { price: number; timestamp: number; symbol: string };
  height?: number;
}

const AGENT_COLORS: Record<string, { primary: string; bg: string }> = {
  paper:   { primary: "#2563eb", bg: "rgba(37,99,235,0.15)" },
  scalper: { primary: "#f59e0b", bg: "rgba(245,158,11,0.15)" },
  worker:  { primary: "#7c3aed", bg: "rgba(124,58,237,0.15)" },
};

const TF_SECONDS: Record<string, number> = {
  "15m": 900, "30m": 1800, "45m": 2700, "1h": 3600,
};

const TIMEFRAMES = [
  { label: "15m", value: "15m" },
  { label: "1h", value: "1h" },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

function toChartCandle(c: { time: number; open: number; high: number; low: number; close: number }): CandlestickData {
  return {
    time: Number(c.time) as UTCTimestamp,
    open: Number(c.open),
    high: Number(c.high),
    low: Number(c.low),
    close: Number(c.close),
  };
}

function tradeToMarker(trade: TradeMarker): any {
  const isOpen = trade.is_open;
  const isWin = (trade.pnl_pct ?? 0) >= 0;

  if (isOpen) {
    // Marker de abertura
    return {
      time: trade.open_time as UTCTimestamp,
      position: trade.side === "LONG" ? "belowBar" : "aboveBar",
      color: trade.side === "LONG" ? "#10b981" : "#ef4444",
      shape: trade.side === "LONG" ? "arrowUp" as any : "arrowDown" as any,
      text: `${trade.side} @ $${trade.open_price.toLocaleString()}`,
      size: 1,
    };
  }

  // Marker de fechamento
  return {
    time: (trade.close_time ?? trade.open_time) as UTCTimestamp,
    position: isWin ? "aboveBar" : "belowBar",
    color: isWin ? "#10b981" : "#ef4444",
    shape: "circle" as any,
    text: `${isWin ? "+" : ""}${trade.pnl_pct?.toFixed(2)}%`,
    size: 1,
  };
}

// ── Component ────────────────────────────────────────────────────────────────

export function AgentChart({ agent, symbol, livePrice, height = 400 }: AgentChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [timeframe, setTimeframe] = useState("1h");
  const [loading, setLoading] = useState(true);
  const [trades, setTrades] = useState<TradeMarker[]>([]);

  const lastSeriesTimeRef = useRef<number>(0);
  const lastCandleRef = useRef<any>(null);

  const colors = AGENT_COLORS[agent] || AGENT_COLORS.paper;

  // ── Init chart ───────────────────────────────────────────────────────────

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0a0e1a" },
        textColor: "#9ca3af",
      },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      timeScale: {
        borderColor: "#1f2937",
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: "#1f2937",
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { labelBackgroundColor: "#374151" },
        horzLine: { labelBackgroundColor: "#374151" },
      },
      width: containerRef.current.clientWidth,
      height: height,
    });

    const series = chart.addCandlestickSeries({
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  // ── Load candles + trade markers ────────────────────────────────────────

  const loadData = useCallback(async () => {
    if (!seriesRef.current) return;
    setLoading(true);

    lastSeriesTimeRef.current = 0;
    lastCandleRef.current = null;

    try {
      // Carregar candles
      const candleRes = await fetch(
        `/api/v1/market/candles?symbol=${symbol}&timeframe=${timeframe}&limit=200`
      );
      const candles = await candleRes.json();

      if (seriesRef.current && candles.length > 0) {
        seriesRef.current.setData(candles.map(toChartCandle));
        const last = candles[candles.length - 1];
        lastCandleRef.current = last;
        lastSeriesTimeRef.current = Number(last.time);
      }

      // Carregar markers de trades
      const tradesRes = await fetch(
        `/api/v1/agents/chart-data/${agent}?symbol=${symbol}&limit=200`
      );
      const tradesData = await tradesRes.json();
      const tradeMarkers = (tradesData.trades || []) as TradeMarker[];
      setTrades(tradeMarkers);

      // Adicionar markers ao chart
      if (seriesRef.current && tradeMarkers.length > 0) {
        const markers = tradeMarkers
          .map(tradeToMarker)
          .filter(Boolean)
          .sort((a: any, b: any) => a.time - b.time);
        seriesRef.current.setMarkers(markers);
      }

      chartRef.current?.timeScale().fitContent();
    } catch (err) {
      console.error("[AgentChart] Erro ao carregar dados:", err);
    }

    setLoading(false);
  }, [agent, symbol, timeframe]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ── Real-time price update ──────────────────────────────────────────────

  useEffect(() => {
    if (!livePrice || !seriesRef.current) return;
    if (livePrice.symbol !== symbol) return;

    const lastSeriesTime = lastSeriesTimeRef.current;
    const lastCandle = lastCandleRef.current;
    if (lastSeriesTime === 0 || !lastCandle) return;

    const intervalSec = TF_SECONDS[timeframe] ?? 3600;
    const priceTimeSec = Math.floor(Number(livePrice.timestamp) / 1000);
    const candleStart = Math.floor(priceTimeSec / intervalSec) * intervalSec;

    if (!Number.isFinite(candleStart) || candleStart <= 0) return;
    if (candleStart < lastSeriesTime) return;

    const isCurrentBar = candleStart === lastSeriesTime;
    const updatedCandle: CandlestickData = {
      time: candleStart as UTCTimestamp,
      open: isCurrentBar ? lastCandle.open : livePrice.price,
      high: isCurrentBar ? Math.max(lastCandle.high, livePrice.price) : livePrice.price,
      low: isCurrentBar ? Math.min(lastCandle.low, livePrice.price) : livePrice.price,
      close: livePrice.price,
    };

    try {
      seriesRef.current.update(updatedCandle);
      lastSeriesTimeRef.current = candleStart;
      lastCandleRef.current = {
        time: candleStart,
        open: updatedCandle.open,
        high: updatedCandle.high,
        low: updatedCandle.low,
        close: updatedCandle.close,
        volume: lastCandle.volume,
      };
    } catch (err) {
      console.warn(`[AgentChart] Erro update: ${err}`);
    }
  }, [livePrice, symbol, timeframe]);

  // ── Stats from trades ───────────────────────────────────────────────────

  const stats = {
    total: trades.length,
    open: trades.filter((t) => t.is_open).length,
    wins: trades.filter((t) => !t.is_open && (t.pnl_pct ?? 0) >= 0).length,
    totalPnl: trades.reduce((sum, t) => sum + (t.pnl ?? 0), 0),
  };
  const winRate = stats.total - stats.open > 0
    ? (stats.wins / (stats.total - stats.open) * 100).toFixed(1)
    : "—";

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#1f2937]">
        <div className="flex items-center gap-3">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: colors.primary }}
          />
          <div>
            <h3 className="text-sm font-bold text-white">
              {agent.toUpperCase()} — {symbol.replace("USDT", "")}/USDT
            </h3>
            <p className="text-[10px] text-[#6b7280]">
              {stats.total} trades · {stats.open} abertos · WR {winRate}%
            </p>
          </div>
        </div>

        {/* Mini stats */}
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[9px] text-[#6b7280] block">P&L</span>
            <span className={`text-xs font-bold ${stats.totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {stats.totalPnl >= 0 ? "+" : ""}${stats.totalPnl.toFixed(2)}
            </span>
          </div>

          {/* Timeframe selector */}
          <div className="flex gap-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                onClick={() => setTimeframe(tf.value)}
                className={clsx(
                  "px-2 py-0.5 text-[10px] rounded font-medium transition-colors",
                  timeframe === tf.value
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "bg-[#1f2937] text-[#9ca3af] hover:text-white border border-transparent"
                )}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#0a0e1a]/80 z-10">
            <div className="flex flex-col items-center gap-2">
              <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-xs text-[#6b7280]">Carregando...</span>
            </div>
          </div>
        )}
        <div ref={containerRef} className="w-full" />
      </div>

      {/* Trade list mini */}
      {trades.length > 0 && (
        <div className="px-4 py-2 border-t border-[#1f2937] max-h-32 overflow-y-auto">
          <div className="text-[9px] text-[#4b5563] mb-1 uppercase tracking-wider">
            Últimos Trades
          </div>
          {trades.slice(-5).reverse().map((t) => (
            <div
              key={t.trade_id}
              className="flex items-center justify-between py-0.5 text-[10px]"
            >
              <div className="flex items-center gap-2">
                <span className={t.side === "LONG" ? "text-emerald-400" : "text-red-400"}>
                  {t.side}
                </span>
                <span className="text-[#9ca3af]">
                  @ ${t.open_price.toLocaleString()}
                </span>
              </div>
              <div>
                {t.is_open ? (
                  <span className="text-amber-400 animate-pulse">ABERTO</span>
                ) : (
                  <span className={(t.pnl_pct ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}>
                    {(t.pnl_pct ?? 0) >= 0 ? "+" : ""}{t.pnl_pct?.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
