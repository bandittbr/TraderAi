"use client";

import { motion } from "framer-motion";

interface MetricProp {
  label: string;
  value: string;
  change?: string;
  positive?: boolean;
  sparkData?: number[];
}

const metrics: MetricProp[] = [
  { label: "Balance",  value: "$125,430", change: "+$2,540", positive: true,  sparkData: [100, 102, 101, 103, 105, 107, 108] },
  { label: "Equity",   value: "$128,210", change: "+$3,120", positive: true,  sparkData: [100, 99, 101, 104, 108, 110, 112] },
  { label: "Profit Factor", value: "2.84", change: "+0.32", positive: true },
  { label: "Sharpe Ratio",  value: "1.92", change: "+0.18",  positive: true },
  { label: "Drawdown", value: "-3.21%", change: "-0.45%", positive: false, sparkData: [0, -1, -0.5, -2, -1.5, -3, -2.5] },
  { label: "Win Rate", value: "78.6%", change: "+2.1%", positive: true },
];

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const w = 60;
  const h = 20;
  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((d - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} className="shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" opacity="0.6" />
    </svg>
  );
}

export default function PerformanceMetrics() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.25 }}
      className="rounded-xl p-3"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      <div className="text-[9px] text-[#2d4060] uppercase tracking-widest mb-2.5 font-semibold">📊 Performance Metrics</div>
      <div className="grid grid-cols-6 gap-2">
        {metrics.map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-lg p-2.5 flex flex-col"
            style={{ background: "#050816", border: "1px solid #1a2540" }}
          >
            <div className="flex items-center justify-between">
              <span className="text-[8px] text-[#2d4060] uppercase tracking-wider">{m.label}</span>
              {m.sparkData && <Sparkline data={m.sparkData} color={m.positive ? "#22c55e" : "#ef4444"} />}
            </div>
            <span className="text-sm font-bold font-mono text-white mt-0.5">{m.value}</span>
            {m.change && (
              <span className={`text-[9px] font-mono ${m.positive ? "text-emerald-400" : "text-red-400"}`}>
                {m.change}
              </span>
            )}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
