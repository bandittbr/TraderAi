"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { createChart, IChartApi, ISeriesApi, CandlestickData, Time } from "lightweight-charts";

interface CandleData {
  time: Time;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface MarkerData {
  time: Time;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown";
  text: string;
}

interface AIPrediction {
  direction: "ALTA" | "BAIXA";
  confidence: number;
  target: number;
  stop: number;
}

export default function TradingChart() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<IChartApi | null>(null);
  const candleSeries = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeries = useRef<ISeriesApi<"Histogram"> | null>(null);
  const [price, setPrice] = useState(64850);
  const [change24h, setChange24h] = useState(2.34);
  const [aiPrediction, setAiPrediction] = useState<AIPrediction>({ direction: "ALTA", confidence: 72, target: 71500, stop: 68900 });
  const [activeInterval, setActiveInterval] = useState("1h");
  const [markers, setMarkers] = useState<MarkerData[]>([]);

  // Generate realistic candle data
  const generateCandles = (count: number): CandleData[] => {
    const candles: CandleData[] = [];
    let basePrice = 64500;
    const now = Math.floor(Date.now() / 1000);
    for (let i = count; i >= 0; i--) {
      const t = now - i * 3600;
      const volatility = 0.002 + Math.random() * 0.004;
      const o = basePrice;
      const c = basePrice * (1 + (Math.random() - 0.48) * volatility);
      const h = Math.max(o, c) * (1 + Math.random() * volatility * 0.5);
      const l = Math.min(o, c) * (1 - Math.random() * volatility * 0.5);
      candles.push({ time: t as Time, open: o, high: h, low: l, close: c, volume: 100 + Math.random() * 500 });
      basePrice = c;
    }
    return candles;
  };

  // Generate buy/sell markers from agents
  const generateMarkers = (candles: CandleData[]): MarkerData[] => {
    const m: MarkerData[] = [];
    candles.forEach((c, i) => {
      if (i > 10 && i < candles.length - 3 && Math.random() < 0.035) {
        m.push({ time: c.time, position: "belowBar", color: "#22c55e", shape: "arrowUp", text: "BUY" });
      }
      if (i > 10 && i < candles.length - 3 && Math.random() < 0.035) {
        m.push({ time: c.time, position: "aboveBar", color: "#ef4444", shape: "arrowDown", text: "SELL" });
      }
    });
    return m;
  };

  useEffect(() => {
    if (!chartRef.current) return;

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: "#080c14" },
        textColor: "#8aa4c8",
        fontSize: 11,
        fontFamily: "'JetBrains Mono', monospace",
      },
      grid: {
        vertLines: { color: "#141c2e" },
        horzLines: { color: "#141c2e" },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: "#2a5fc8", width: 1, style: 2 },
        horzLine: { color: "#2a5fc8", width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: "#1a2a4a",
        scaleMargins: { top: 0.15, bottom: 0.08 },
      },
      timeScale: {
        borderColor: "#1a2a4a",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true },
      handleScale: { mouseWheel: true, pinch: true },
    });

    chartInstance.current = chart;

    // Candlestick series
    const candles = chart.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      priceFormat: { type: "price", precision: 2, minMove: 0.01 },
    });
    candleSeries.current = candles;

    // Volume series (overlay on bottom)
    const volume = chart.addHistogramSeries({
      color: "#22c55e30",
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      base: 0,
    });
    volumeSeries.current = volume;

    // Apply volume scale
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
      borderVisible: false,
    });

    // Initial data
    const initialCandles = generateCandles(120);
    candles.setData(initialCandles);
    volume.setData(initialCandles.map(c => ({ time: c.time, value: c.volume, color: c.close >= c.open ? "#22c55e30" : "#ef444430" })));
    const newMarkers = generateMarkers(initialCandles);
    setMarkers(newMarkers);
    candles.setMarkers(newMarkers.map(m => ({ time: m.time, position: m.position, color: m.color, shape: m.shape, text: m.text })));

    // Price simulation
    const priceInterval = setInterval(() => {
      const delta = (Math.random() - 0.5) * 200;
      setPrice(p => Math.max(60000, Math.min(75000, p + delta)));
      setChange24h(c => Math.max(-10, Math.min(10, c + (Math.random() - 0.5) * 0.5)));
    }, 3000);

    // AI prediction update
    const aiInterval = setInterval(() => {
      setAiPrediction(p => ({
        direction: Math.random() > 0.5 ? "ALTA" : "BAIXA",
        confidence: 65 + Math.floor(Math.random() * 25),
        target: p.direction === "ALTA" ? 71500 + Math.floor(Math.random() * 2000) : 68900 - Math.floor(Math.random() * 2000),
        stop: p.direction === "ALTA" ? 68900 - Math.floor(Math.random() * 1000) : 71500 + Math.floor(Math.random() * 1000),
      }));
    }, 15000);

    return () => {
      clearInterval(priceInterval);
      clearInterval(aiInterval);
      chart.remove();
      chartInstance.current = null;
    };
  }, []);

  // Update markers when interval changes
  useEffect(() => {
    if (candleSeries.current && chartInstance.current) {
      const newCandles = generateCandles(activeInterval === "15m" ? 200 : activeInterval === "1h" ? 120 : 80);
      candleSeries.current.setData(newCandles);
      volumeSeries.current?.setData(newCandles.map(c => ({ time: c.time, value: c.volume, color: c.close >= c.open ? "#22c55e30" : "#ef444430" })));
      const newMarkers = generateMarkers(newCandles);
      setMarkers(newMarkers);
      candleSeries.current.setMarkers(newMarkers.map(m => ({ time: m.time, position: m.position, color: m.color, shape: m.shape, text: m.text })));
    }
  }, [activeInterval]);

  const lastCandle = generateCandles(1)[0];
  const isUp = lastCandle.close >= lastCandle.open;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="relative rounded-xl overflow-hidden"
      style={{ background: "#080c14", border: "1px solid #1a2a4a" }}
    >
      {/* Chart Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "#1a2a4a" }}>
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-text-primary">BTCUSDT</span>
              <span className={`text-sm font-bold font-mono ${isUp ? "text-neon-green" : "text-neon-red"}`}>
                ${price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
              <span className={`text-[11px] font-medium ${change24h >= 0 ? "text-neon-green" : "text-neon-red"}`}>
                {change24h >= 0 ? "+" : ""}{change24h.toFixed(2)}%
              </span>
            </div>
            <div className="text-[9px] text-text-dim font-mono mt-0.5">Vol: {(lastCandle.volume * 10).toFixed(0)} BTC</div>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-bg-tertiary rounded-lg p-0.5">
          {["15m", "1h", "4h", "1d", "1w"].map(interval => (
            <button
              key={interval}
              onClick={() => setActiveInterval(interval)}
              className={`px-2.5 py-1 text-[10px] font-medium rounded-md transition-all ${
                activeInterval === interval
                  ? "bg-neon-blue/20 text-neon-blue border border-neon-blue/30"
                  : "text-text-dim hover:text-text-secondary"
              }`}
            >
              {interval}
            </button>
          ))}
        </div>
      </div>

      {/* Chart + AI Panel */}
      <div className="flex">
        {/* Chart */}
        <div className="relative" style={{ width: "calc(100% - 220px)", height: 380 }}>
          <div ref={chartRef} style={{ width: "100%", height: "100%" }} />
          
          {/* Agent markers legend */}
          <div className="absolute bottom-2 left-3 flex gap-2">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-neon-green" />
              <span className="text-[8px] text-neon-green font-mono">BUY (Agents)</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-neon-red" />
              <span className="text-[8px] text-neon-red font-mono">SELL (Agents)</span>
            </div>
          </div>
        </div>

        {/* AI Prediction Panel */}
        <div className="w-[220px] border-l p-3 flex flex-col justify-center" style={{ background: "rgba(5,8,22,0.6)", borderColor: "#1a2a4a" }}>
          <div className="text-[9px] text-text-dim uppercase tracking-widest mb-2 font-semibold">AI PREDICTION</div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-neon-blue to-neon-purple flex items-center justify-center text-sm">🤖</div>
            <div>
              <div className="text-xs text-text-primary font-bold">BTCUSDT</div>
              <div className={`text-[10px] font-mono font-bold ${aiPrediction.direction === "ALTA" ? "text-neon-green" : "text-neon-red"}`}>
                {aiPrediction.confidence}% {aiPrediction.direction}
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px]">
              <span className="text-text-dim">Target</span>
              <span className="text-neon-green font-mono font-bold">${aiPrediction.target.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-text-dim">Stop</span>
              <span className="text-neon-red font-mono font-bold">${aiPrediction.stop.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-text-dim">R:R</span>
              <span className="text-text-primary font-mono">1:2.4</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t" style={{ borderColor: "#1a2a4a" }}>
            <div className="text-[9px] text-text-dim uppercase mb-1">Confidence</div>
            <div className="h-1.5 rounded-full bg-border-primary overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${aiPrediction.confidence}%` }}
                transition={{ duration: 1, delay: 0.5 }}
                className="h-full rounded-full bg-gradient-to-r from-neon-blue to-neon-purple"
              />
            </div>
            <div className="text-[10px] text-neon-blue font-mono mt-1">{aiPrediction.confidence}%</div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}