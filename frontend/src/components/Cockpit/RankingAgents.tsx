"use client";

import { useState } from "react";
import { motion } from "framer-motion";

interface RankingEntry {
  rank: number;
  name: string;
  pnl: number;
  winRate: number;
  trades: number;
  color: string;
}

const allAgents: RankingEntry[] = [
  { rank: 1, name: "Scalper Pro",     pnl: 842,  winRate: 82, trades: 28, color: "#f59e0b" },
  { rank: 2, name: "Trend Follower",  pnl: 621,  winRate: 73, trades: 15, color: "#3b82f6" },
  { rank: 3, name: "Breakout Hunter", pnl: 412,  winRate: 67, trades: 12, color: "#8b5cf6" },
  { rank: 4, name: "Reversal Master", pnl: 234,  winRate: 75, trades: 8,  color: "#ec4899" },
  { rank: 5, name: "Momentum RSI",    pnl: 187,  winRate: 68, trades: 22, color: "#ef4444" },
  { rank: 6, name: "News Trader",     pnl: 156,  winRate: 83, trades: 6,  color: "#06b6d4" },
  { rank: 7, name: "Portfolio Cycle", pnl: 98,   winRate: 50, trades: 4,  color: "#10b981" },
];

type Period = "Hoje" | "7D" | "30D" | "Total";
const periods: Period[] = ["Hoje", "7D", "30D", "Total"];

const medals = ["🥇", "🥈", "🥉"];

export default function RankingAgents() {
  const [period, setPeriod] = useState<Period>("Hoje");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.45 }}
      className="rounded-xl p-3"
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-white">🏆</span>
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">Ranking de Agentes</span>
        </div>
        <div className="flex gap-1 bg-[#050816] rounded-lg p-0.5">
          {periods.map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-2 py-0.5 text-[9px] font-medium rounded-md transition-all ${
                period === p
                  ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                  : "text-[#2d4060] hover:text-[#4a6080]"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Rankings */}
      <div className="space-y-1">
        {allAgents.map((agent, i) => {
          const isMedal = i < 3;
          const maxPnl = Math.max(...allAgents.map(a => a.pnl));
          const barWidth = maxPnl > 0 ? (agent.pnl / maxPnl) * 100 : 0;

          return (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
              className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#0a0e1a40] transition-colors relative overflow-hidden"
            >
              {/* Background bar */}
              <div
                className="absolute left-0 top-0 bottom-0 rounded-lg transition-all duration-500"
                style={{ width: `${barWidth}%`, background: `${agent.color}08` }}
              />

              {/* Rank */}
              <div className="w-6 text-center relative">
                {isMedal ? (
                  <span className="text-sm">{medals[i]}</span>
                ) : (
                  <span className="text-[10px] text-[#2d4060] font-mono">#{agent.rank}</span>
                )}
              </div>

              {/* Name */}
              <div className="flex-1 relative">
                <span className="text-[10px] text-white font-medium">{agent.name}</span>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-3 relative">
                <div className="text-right">
                  <div className={`text-[10px] font-bold font-mono ${agent.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {agent.pnl >= 0 ? "+" : ""}${agent.pnl.toLocaleString()}
                  </div>
                </div>
                <div className="text-right w-10">
                  <div className="text-[9px] font-mono text-[#2d4060]">{agent.trades}t</div>
                </div>
                <div className="text-right w-10">
                  <div className="text-[9px] font-mono text-emerald-400">{agent.winRate}%</div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
