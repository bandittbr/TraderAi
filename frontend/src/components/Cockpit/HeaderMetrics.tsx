"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

interface HeaderMetricsProps {
  systemStatus: "online" | "degraded" | "offline";
  totalCapital: number;
  totalInitial: number;
  tradesToday: number;
  winRate: number;
}

function AnimatedNumber({ value, prefix = "", suffix = "", decimals = 2, color }: {
  value: number; prefix?: string; suffix?: string; decimals?: number; color?: string;
}) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const duration = 800;
    const steps = 30;
    const stepTime = duration / steps;
    let step = 0;
    const interval = setInterval(() => {
      step++;
      const progress = step / steps;
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (step >= steps) { clearInterval(interval); setDisplay(value); }
    }, stepTime);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  const formatted = display.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return <span className={color ?? "text-white"}>{prefix}{formatted}{suffix}</span>;
}

function MetricItem({ label, value, prefix, suffix, decimals, color, sub }: {
  label: string; value: number; prefix?: string; suffix?: string; decimals?: number; color?: string; sub?: string;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-[#2d4060] uppercase tracking-widest font-medium">{label}</span>
      <div className="flex items-baseline gap-1">
        <span className="text-sm font-bold font-mono">
          <AnimatedNumber value={value} prefix={prefix ?? ""} suffix={suffix ?? ""} decimals={decimals ?? 2} color={color} />
        </span>
        {sub && <span className="text-[10px] text-[#2d4060]">{sub}</span>}
      </div>
    </div>
  );
}

const statusConfig = {
  online:    { dot: "bg-emerald-500 shadow-[0_0_8px_#10b981]", text: "ONLINE",   color: "text-emerald-400" },
  degraded:  { dot: "bg-amber-500 shadow-[0_0_8px_#f59e0b]",   text: "DEGRADED", color: "text-amber-400"   },
  offline:   { dot: "bg-red-500 shadow-[0_0_8px_#ef4444]",     text: "OFFLINE",  color: "text-red-400"      },
};

export default function HeaderMetrics({ systemStatus, totalCapital, totalInitial, tradesToday, winRate }: HeaderMetricsProps) {
  const totalPnl = totalCapital - totalInitial;
  const totalPnlPct = totalInitial > 0 ? (totalPnl / totalInitial) * 100 : 0;
  const status = statusConfig[systemStatus] ?? statusConfig.offline;

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex items-center justify-between px-5 py-3 rounded-xl"
      style={{ background: "linear-gradient(135deg, #0a0e1a 0%, #0d1525 100%)", border: "1px solid #1a2540" }}
    >
      {/* Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "#05081640", border: "1px solid #1a2540" }}>
          <span className={`w-2 h-2 rounded-full ${status.dot}`} />
          <span className={`text-[11px] font-bold tracking-wider ${status.color}`}>{status.text}</span>
        </div>
        <div className="h-6 w-px bg-[#1a2540]" />
        <div>
          <span className="text-[10px] text-[#2d4060] uppercase tracking-widest">TRADEAI COCKPIT</span>
          <div className="text-[10px] text-[#3d5a80] font-mono">v14.0.0 · Multi-Agent</div>
        </div>
      </div>

      {/* Metrics */}
      <div className="flex items-center gap-6">
        <MetricItem label="Capital Total" value={totalCapital} prefix="$" color="text-white" />
        <div className="h-8 w-px bg-[#1a2540]" />
        <MetricItem
          label="P&L Total"
          value={Math.abs(totalPnl)}
          prefix={totalPnl >= 0 ? "+$" : "-$"}
          color={totalPnl >= 0 ? "text-emerald-400" : "text-red-400"}
          sub={totalPnlPct >= 0 ? `+${totalPnlPct.toFixed(2)}%` : `${totalPnlPct.toFixed(2)}%`}
        />
        <div className="h-8 w-px bg-[#1a2540]" />
        <MetricItem label="Drawdown" value={3.21} prefix="-" suffix="%" decimals={2} color="text-red-400" />
        <div className="h-8 w-px bg-[#1a2540]" />
        <MetricItem label="Win Rate" value={winRate} suffix="%" decimals={1} color="text-emerald-400" />
        <div className="h-8 w-px bg-[#1a2540]" />
        <MetricItem label="Trades Hoje" value={tradesToday} decimals={0} color="text-blue-400" />
      </div>

      {/* User */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "#05081640", border: "1px solid #1a2540" }}>
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-[10px] font-bold text-white">
          TR
        </div>
        <div>
          <div className="text-[11px] text-white font-medium">Trader</div>
          <div className="text-[9px] text-[#2d4060]">Fund Manager</div>
        </div>
      </div>
    </motion.header>
  );
}
