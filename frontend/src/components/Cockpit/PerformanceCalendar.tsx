"use client";

import { motion } from "framer-motion";

export default function PerformanceCalendar() {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];

  // Mock performance data - green for positive days, red for negative
  const performanceData: Record<number, "positive" | "negative" | "neutral"> = {};
  for (let d = 1; d <= daysInMonth; d++) {
    const rand = Math.random();
    if (rand < 0.55) performanceData[d] = "positive";
    else if (rand < 0.85) performanceData[d] = "negative";
    else performanceData[d] = "neutral";
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.55 }}
      className="rounded-xl p-3"
      style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-text-primary">📅</span>
          <span className="text-[10px] font-bold text-text-primary uppercase tracking-wider">Calendário de Performance</span>
        </div>
        <div className="text-[9px] text-text-primary font-mono">
          {monthNames[month]} {year}
        </div>
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 gap-1 mb-1">
        {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map((day, i) => (
          <div key={day} className="text-center text-[8px] font-medium text-text-dim uppercase tracking-wider py-1">
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7 gap-1">
        {/* Empty cells before first day */}
        {Array.from({ length: firstDay }, (_, i) => (
          <div key={`empty-${i}`} className="aspect-square" />
        ))}

        {/* Days */}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const day = i + 1;
          const isToday = day === today.getDate();
          const perf = performanceData[day];
          const isPositive = perf === "positive";
          const isNegative = perf === "negative";

          return (
            <motion.div
              key={day}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: day * 0.01 }}
              className="relative aspect-square flex items-center justify-center rounded-lg transition-all cursor-default"
              style={{
                background: isToday
                  ? "rgba(59, 130, 246, 0.15)"
                  : isPositive
                  ? "rgba(16, 185, 129, 0.08)"
                  : isNegative
                  ? "rgba(239, 68, 68, 0.08)"
                  : "transparent",
                border: isToday
                  ? "1px solid #3b82f6"
                  : isPositive
                  ? "1px solid #22c55e30"
                  : isNegative
                  ? "1px solid #ef444430"
                  : "1px solid #1a2a4a",
              }}
            >
              <span className={`text-[10px] font-mono font-medium ${isToday ? "text-neon-blue" : isPositive ? "text-neon-green" : isNegative ? "text-neon-red" : "text-text-secondary"}`}>
                {day}
              </span>
              {/* Performance indicator dot */}
              {(isPositive || isNegative) && (
                <span className="absolute bottom-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full" style={{ background: isPositive ? "#22c55e" : "#ef4444" }} />
              )}
              {isToday && (
                <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-neon-blue" />
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-3 pt-2 border-t" style={{ borderColor: "#1a2a4a" }}>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-neon-green" />
          <span className="text-[9px] text-text-dim">Positivo</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-neon-red" />
          <span className="text-[9px] text-text-dim">Negativo</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-neon-blue" />
          <span className="text-[9px] text-text-dim">Hoje</span>
        </div>
      </div>
    </motion.div>
  );
}