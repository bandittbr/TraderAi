"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface HeaderMetricsProps {
  systemStatus: "online" | "degraded" | "offline";
  totalCapital: number;
  totalInitial: number;
  pnlToday: number;
  pnlMonth: number;
  drawdown: number;
  winRate: number;
  tradesToday: number;
  userName?: string;
  userRole?: string;
}

const statusConfig = {
  online: { dot: "bg-neon-green", text: "ONLINE", glow: "shadow-glow-green", ring: "ring-neon-green/30" },
  degraded: { dot: "bg-neon-amber", text: "DEGRADED", glow: "shadow-[0_0_8px_#f59e0b]", ring: "ring-neon-amber/30" },
  offline: { dot: "bg-neon-red", text: "OFFLINE", glow: "shadow-glow-red", ring: "ring-neon-red/30" },
};

function AnimatedCounter({ value, prefix = "", suffix = "", decimals = 2, className = "", colorClass = "text-text-primary" }: {
  value: number; prefix?: string; suffix?: string; decimals?: number; className?: string; colorClass?: string;
}) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const duration = 600;
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
  }, [value]);

  const formatted = display.toLocaleString("pt-BR", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return (
    <span className={`font-mono font-semibold ${colorClass} ${className}`}>
      <span className="text-text-muted">{prefix}</span>{formatted}<span className="text-text-muted">{suffix}</span>
    </span>
  );
}

function MetricItem({ label, value, prefix, suffix, decimals, colorClass, subLabel }: {
  label: string; value: number; prefix?: string; suffix?: string; decimals?: number; colorClass?: string; subLabel?: string;
}) {
  return (
    <div className="flex flex-col min-w-[120px]" style={{ minWidth: "120px" }}>
      <span className="text-[10px] font-medium text-text-dim uppercase tracking-wider mb-1">{label}</span>
      <div className="flex items-baseline gap-1">
        <AnimatedCounter value={value} prefix={prefix} suffix={suffix} decimals={decimals ?? 2} colorClass={colorClass} />
        {subLabel && <span className="text-[10px] text-text-dim ml-1">{subLabel}</span>}
      </div>
    </div>
  );
}

export default function HeaderMetrics({
  systemStatus,
  totalCapital,
  totalInitial,
  pnlToday,
  pnlMonth,
  drawdown,
  winRate,
  tradesToday,
  userName = "Trader",
  userRole = "Fund Manager",
}: HeaderMetricsProps) {
  const totalPnl = totalCapital - totalInitial;
  const totalPnlPct = totalInitial > 0 ? (totalPnl / totalInitial) * 100 : 0;
  const status = statusConfig[systemStatus];

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative flex items-center justify-between px-5 py-3 rounded-xl"
      style={{
        background: "linear-gradient(135deg, rgba(5,8,22,0.95) 0%, rgba(13,20,38,0.95) 100%)",
        border: "1px solid #1a2a4a",
        backdropFilter: "blur(20px)",
      }}
    >
      {/* Glow top border */}
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ background: "linear-gradient(90deg, transparent, #2a5fc8, transparent)" }} />

      {/* Left: System Status + Brand */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "rgba(5,8,22,0.6)", border: "1px solid #1a2a4a" }}>
          <motion.span
            className={`w-2 h-2 rounded-full ${status.dot} ${status.glow}`}
            animate={{ boxShadow: status.glow === "shadow-glow-green" ? "0 0 12px #10b981" : status.glow === "shadow-[0_0_8px_#f59e0b]" ? "0 0 12px #f59e0b" : "0 0 12px #ef4444" }}
            transition={{ duration: 1.5, repeat: Infinity }}
          />
          <span className={`text-[11px] font-bold tracking-wider ${status.text === "ONLINE" ? "text-neon-green" : status.text === "DEGRADED" ? "text-neon-amber" : "text-neon-red"}`}>
            {status.text}
          </span>
        </div>
        <div className="h-6 w-px bg-border-primary" />
        <div>
          <div className="text-[10px] font-bold text-text-primary tracking-widest uppercase">TRADEAI COCKPIT</div>
          <div className="text-[9px] text-text-dim font-mono">v14.0.0 · Multi-Agent</div>
        </div>
      </div>

      {/* Center: Financial Metrics */}
      <div className="flex items-center gap-6 flex-1 justify-center min-w-0">
        <MetricItem label="Capital Total" value={totalCapital} prefix="R$ " colorClass="text-text-primary" />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem
          label="P&L Total"
          value={Math.abs(totalPnl)}
          prefix={totalPnl >= 0 ? "+R$ " : "-R$ "}
          colorClass={totalPnl >= 0 ? "text-neon-green" : "text-neon-red"}
          subLabel={totalPnlPct >= 0 ? `+${totalPnlPct.toFixed(2)}%` : `${totalPnlPct.toFixed(2)}%`}
        />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem label="P&L Hoje" value={Math.abs(pnlToday)} prefix={pnlToday >= 0 ? "+R$ " : "-R$ "} colorClass={pnlToday >= 0 ? "text-neon-green" : "text-neon-red"} />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem label="P&L Mês" value={Math.abs(pnlMonth)} prefix={pnlMonth >= 0 ? "+R$ " : "-R$ "} colorClass={pnlMonth >= 0 ? "text-neon-green" : "text-neon-red"} />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem label="Drawdown" value={drawdown} prefix="-" suffix="%" decimals={2} colorClass="text-neon-red" />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem label="Win Rate" value={winRate} suffix="%" decimals={1} colorClass="text-neon-green" />
        <div className="h-8 w-px bg-border-secondary" />
        <MetricItem label="Trades Hoje" value={tradesToday} decimals={0} colorClass="text-neon-blue" />
      </div>

      {/* Right: User */}
      <div className="flex items-center gap-3 px-3 py-1.5 rounded-lg" style={{ background: "rgba(5,8,22,0.6)", border: "1px solid #1a2a4a" }}>
        <div className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold text-text-primary" style={{ background: "linear-gradient(135deg, #3b82f6, #8b5cf6)" }}>
          {userName.slice(0,2).toUpperCase()}
        </div>
        <div className="text-right hidden sm:block">
          <div className="text-[11px] font-semibold text-text-primary">{userName}</div>
          <div className="text-[9px] text-text-dim">{userRole}</div>
        </div>
      </div>
    </motion.header>
  );
}