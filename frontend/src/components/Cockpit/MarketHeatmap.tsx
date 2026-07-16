"use client";

import { motion } from "framer-motion";

const assets = [
  { symbol: "BTC",  price: 64850, change: 2.34,  impact: "high" as const },
  { symbol: "ETH",  price: 3452,  change: 1.87,  impact: "high" as const },
  { symbol: "BNB",  price: 587,   change: -0.45, impact: "high" as const },
  { symbol: "SOL",  price: 142,   change: 5.12,  impact: "high" as const },
  { symbol: "XRP",  price: 0.58,  change: -1.23, impact: "medium" as const },
  { symbol: "ADA",  price: 0.45,  change: 3.78,  impact: "medium" as const },
  { symbol: "DOGE", price: 0.12,  change: -2.15, impact: "medium" as const },
  { symbol: "AVAX", price: 35.8,  change: 4.56,  impact: "medium" as const },
  { symbol: "LINK", price: 14.2,  change: -0.89, impact: "low" as const },
  { symbol: "MATIC",price: 0.72,  change: 1.05,  impact: "low" as const },
];

function getColor(change: number): string {
  if (change > 3) return "#22c55e";
  if (change > 1) return "#16a34a";
  if (change > 0) return "#4ade8070";
  if (change > -1) return "#ef444470";
  if (change > -3) return "#dc2626";
  return "#b91c1c";
}

function getBgColor(change: number): string {
  if (change > 3) return "#22c55e15";
  if (change > 1) return "#16a34a10";
  if (change > 0) return "#4ade8008";
  if (change > -1) return "#ef444408";
  if (change > -3) return "#dc262610";
  return "#b91c1c15";
}

export default function MarketHeatmap() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="rounded-xl p-3"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-white">🔥</span>
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">Heatmap</span>
        </div>
        <span className="text-[8px] text-[#2d4060] font-mono">live</span>
      </div>

      <div className="grid grid-cols-5 gap-1.5">
        {assets.map((asset, i) => (
          <motion.div
            key={asset.symbol}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.03 }}
            className="rounded-lg p-2 text-center transition-all hover:scale-105 cursor-pointer"
            style={{ background: getBgColor(asset.change), border: `1px solid ${getColor(asset.change)}30` }}
          >
            <div className="text-[10px] font-bold text-white">{asset.symbol}</div>
            <div className="text-[9px] font-mono text-[#8aa4c8]">
              ${asset.price.toLocaleString(undefined, { maximumFractionDigits: asset.price < 1 ? 4 : asset.price < 10 ? 2 : 0 })}
            </div>
            <div className={`text-[9px] font-mono font-bold ${asset.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {asset.change >= 0 ? "+" : ""}{asset.change.toFixed(2)}%
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
