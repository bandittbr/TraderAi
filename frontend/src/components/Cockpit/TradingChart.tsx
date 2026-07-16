"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface MarkerData {
  time: number;
  position: "aboveBar" | "belowBar";
  color: string;
  shape: "arrowUp" | "arrowDown";
  text: string;
}

// Fallback: lightweight-charts may not SSR — we render a professional SVG chart
export default function TradingChart() {
  const [price, setPrice] = useState(64850);
  const [change24h, setChange24h] = useState(2.34);
  const [aiPrediction, setAiPrediction] = useState({ direction: "ALTA", confidence: 72, target: 71500, stop: 68900 });
  const [activeInterval, setActiveInterval] = useState("1h");

  useEffect(() => {
    const int = setInterval(() => {
      const delta = (Math.random() - 0.5) * 200;
      setPrice(p => Math.max(60000, Math.min(75000, p + delta)));
      setChange24h(c => Math.max(-10, Math.min(10, c + (Math.random() - 0.5) * 0.5)));
    }, 3000);
    return () => clearInterval(int);
  }, []);

  // Generate realistic candlestick data
  const candles: CandleData[] = [];
  let basePrice = 64500;
  const now = Math.floor(Date.now() / 1000);
  const daySeconds = 24 * 60 * 60;
  for (let i = 60; i >= 0; i--) {
    const t = now - i * 3600;
    const volatility = 0.002 + Math.random() * 0.004;
    const o = basePrice;
    const c = basePrice * (1 + (Math.random() - 0.48) * volatility);
    const h = Math.max(o, c) * (1 + Math.random() * volatility * 0.5);
    const l = Math.min(o, c) * (1 - Math.random() * volatility * 0.5);
    candles.push({ time: t, open: o, high: h, low: l, close: c, volume: 100 + Math.random() * 500 });
    basePrice = c;
  }

  // EMAs (simulated)
  const ema9 = candles.reduce((s, c, i) => {
    if (i < 9) return s;
    return [...s.slice(0, -1), candles.slice(i - 8, i + 1).reduce((a, b) => a + b.close, 0) / 9];
  }, [] as number[]);
  const ema50 = candles.reduce((s, c, i) => {
    if (i < 50 || i % 5 !== 0) return s;
    return [...s.slice(0, -1), candles.slice(i - 4, i + 1).reduce((a, b) => a + b.close, 0) / 5];
  }, [] as number[]);

  // Buy/Sell markers from agents
  const markers: MarkerData[] = [];
  candles.forEach((c, i) => {
    if (i > 10 && i < candles.length - 3 && Math.random() < 0.04) {
      markers.push({
        time: c.time,
        position: "belowBar",
        color: "#22c55e",
        shape: "arrowUp",
        text: "BUY",
      });
    }
    if (i > 10 && i < candles.length - 3 && Math.random() < 0.04) {
      markers.push({
        time: c.time,
        position: "aboveBar",
        color: "#ef4444",
        shape: "arrowDown",
        text: "SELL",
      });
    }
  });

  // Chart dimensions
  const chartW = 680;
  const chartH = 320;
  const padding = { top: 20, right: 60, bottom: 50, left: 60 };

  const minPrice = Math.min(...candles.map(c => c.low)) * 0.998;
  const maxPrice = Math.max(...candles.map(c => c.high)) * 1.002;
  const priceRange = maxPrice - minPrice;
  const maxVol = Math.max(...candles.map(c => c.volume));

  const xPos = (i: number) => padding.left + (i / (candles.length - 1)) * (chartW - padding.left - padding.right);
  const yPrice = (p: number) => padding.top + ((maxPrice - p) / priceRange) * (chartH - padding.top - padding.bottom - 60);
  const yVol = (v: number) => chartH - 40 - (v / maxVol) * 40;

  const lastCandle = candles[candles.length - 1];
  const isUp = lastCandle.close >= lastCandle.open;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.1 }}
      className="rounded-xl overflow-hidden"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      {/* Chart Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1a2540]">
        <div className="flex items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-white">BTCUSDT</span>
              <span className={`text-sm font-bold font-mono ${isUp ? "text-emerald-400" : "text-red-400"}`}>
                ${price.toLocaleString("en-US", { minimumFractionDigits: 2 })}
              </span>
              <span className={`text-[11px] font-medium ${change24h >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                {change24h >= 0 ? "+" : ""}{change24h.toFixed(2)}%
              </span>
            </div>
            <div className="text-[9px] text-[#2d4060] font-mono">Vol: {(lastCandle.volume * 10).toFixed(0)} BTC</div>
          </div>
        </div>
        <div className="flex items-center gap-1 bg-[#050816] rounded-lg p-0.5">
          {["15m", "1h", "4h", "1d", "1w"].map(interval => (
            <button
              key={interval}
              onClick={() => setActiveInterval(interval)}
              className={`px-2.5 py-1 text-[10px] font-medium rounded-md transition-all ${
                activeInterval === interval
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "text-[#2d4060] hover:text-[#4a6080]"
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
        <div className="relative" style={{ width: chartW, height: chartH }}>
          <svg width={chartW} height={chartH} className="absolute inset-0">
            {/* Grid */}
            {Array.from({ length: 5 }).map((_, i) => {
              const y = padding.top + (i / 4) * (chartH - padding.top - padding.bottom - 60);
              return (
                <g key={`grid-${i}`}>
                  <line x1={padding.left} y1={y} x2={chartW - padding.right} y2={y} stroke="#141c2e" strokeWidth="1" />
                  <text x={padding.left - 8} y={y + 3} textAnchor="end" fill="#2d4060" fontSize="9" fontFamily="monospace">
                    ${(maxPrice - (i / 4) * priceRange).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </text>
                </g>
              );
            })}

            {/* Candles */}
            {candles.map((c, i) => {
              if (i % 2 !== 0) return null;
              const x = xPos(i);
              const bodyTop = Math.min(yPrice(c.open), yPrice(c.close));
              const bodyBottom = Math.max(yPrice(c.open), yPrice(c.close));
              const bodyH = Math.max(1, bodyBottom - bodyTop);
              const isGreen = c.close >= c.open;
              return (
                <g key={i}>
                  <line x1={x} y1={yPrice(c.high)} x2={x} y2={yPrice(c.low)} stroke={isGreen ? "#22c55e" : "#ef4444"} strokeWidth="1" />
                  <rect x={x - 2} y={bodyTop} width={4} height={bodyH} fill={isGreen ? "#22c55e" : "#ef4444"} rx="0.5" />
                </g>
              );
            })}

            {/* EMAs */}
            {ema9.length > 0 && (
              <path
                d={candles.map((c, i) => {
                  if (i < 9) return "";
                  const x = xPos(i);
                  const y = yPrice(ema9[i - 9] || c.close);
                  return `${i === 9 ? "M" : "L"}${x},${y}`;
                }).join(" ")}
                stroke="#3b82f6"
                strokeWidth="1"
                fill="none"
                opacity="0.7"
              />
            )}

            {/* Buy/Sell markers */}
            {markers.map((m, i) => {
              const idx = candles.findIndex(c => c.time === m.time);
              if (idx < 0) return null;
              const x = xPos(idx);
              const y = m.position === "belowBar" ? yPrice(candles[idx].low) - 12 : yPrice(candles[idx].high) + 8;
              return (
                <g key={`marker-${i}`}>
                  <text x={x} y={y} textAnchor="middle" fill={m.color} fontSize="10" fontWeight="bold">
                    {m.shape === "arrowUp" ? "▲" : "▼"}
                  </text>
                  <text x={x} y={y + (m.position === "belowBar" ? 12 : -10)} textAnchor="middle" fill={m.color} fontSize="7">
                    {m.text}
                  </text>
                </g>
              );
            })}

            {/* Volume bars */}
            {candles.map((c, i) => {
              if (i % 3 !== 0) return null;
              const x = xPos(i);
              const h = yVol(c.volume);
              const isGreen = c.close >= c.open;
              return (
                <rect
                  key={`vol-${i}`}
                  x={x - 1.5}
                  y={h}
                  width={3}
                  height={chartH - 40 - h}
                  fill={isGreen ? "#22c55e20" : "#ef444420"}
                  rx="0.5"
                />
              );
            })}
          </svg>

          {/* Agent markers overlay labels */}
          <div className="absolute bottom-2 left-3 flex gap-2">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-[8px] text-emerald-400 font-mono">BUY (Agents)</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-[8px] text-red-400 font-mono">SELL (Agents)</span>
            </div>
          </div>
        </div>

        {/* AI Prediction Panel */}
        <div className="w-[180px] border-l border-[#1a2540] p-3 flex flex-col justify-center" style={{ background: "#05081660" }}>
          <div className="text-[9px] text-[#2d4060] uppercase tracking-widest mb-2 font-semibold">AI PREDICTION</div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-sm">
              🤖
            </div>
            <div>
              <div className="text-xs text-white font-bold">BTCUSDT</div>
              <div className={`text-[10px] font-mono font-bold ${aiPrediction.direction === "ALTA" ? "text-emerald-400" : "text-red-400"}`}>
                {aiPrediction.confidence}% {aiPrediction.direction}
              </div>
            </div>
          </div>
          <div className="space-y-1.5">
            <div className="flex justify-between text-[10px]">
              <span className="text-[#2d4060]">Target</span>
              <span className="text-emerald-400 font-mono font-bold">${aiPrediction.target.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#2d4060]">Stop</span>
              <span className="text-red-400 font-mono font-bold">${aiPrediction.stop.toLocaleString()}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#2d4060]">R:R</span>
              <span className="text-white font-mono">1:2.4</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[#1a2540]">
            <div className="text-[9px] text-[#2d4060] uppercase mb-1">Confidence</div>
            <div className="h-1.5 rounded-full bg-[#1a2540] overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${aiPrediction.confidence}%` }}
                transition={{ duration: 1, delay: 0.5 }}
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-purple-500"
              />
            </div>
            <div className="text-[10px] text-blue-400 font-mono mt-1">{aiPrediction.confidence}%</div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
