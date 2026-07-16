"use client";

import { motion } from "framer-motion";

interface AgentData {
  name: string;
  strategy: string;
  status: "online" | "idle" | "offline";
  pnlToday: number;
  trades: number;
  winRate: number;
  capital: number;
  color: string;
  icon: string;
}

const agents: AgentData[] = [
  { name: "Scalper Pro",     strategy: "Grid Scalping",        status: "online", pnlToday: 842,  trades: 28, winRate: 82, capital: 25000, color: "#f59e0b", icon: "⚡" },
  { name: "Trend Follower",  strategy: "Trend Following",      status: "online", pnlToday: 621,  trades: 15, winRate: 73, capital: 20000, color: "#3b82f6", icon: "📈" },
  { name: "Breakout Hunter", strategy: "Breakout",             status: "online", pnlToday: 412,  trades: 12, winRate: 67, capital: 15000, color: "#8b5cf6", icon: "💥" },
  { name: "Reversal Master", strategy: "Mean Reversion",       status: "idle",   pnlToday: 234,  trades: 8,  winRate: 75, capital: 12000, color: "#ec4899", icon: "🔄" },
  { name: "Momentum RSI",    strategy: "Momentum + RSI",       status: "online", pnlToday: 187,  trades: 22, winRate: 68, capital: 18000, color: "#ef4444", icon: "📊" },
  { name: "News Trader",     strategy: "AI Combined",          status: "online", pnlToday: 156,  trades: 6,  winRate: 83, capital: 10000, color: "#06b6d4", icon: "📰" },
  { name: "Portfolio Cycle", strategy: "Rotação Setorial",     status: "idle",   pnlToday: 98,   trades: 4,  winRate: 50, capital: 8000,  color: "#10b981", icon: "🔄" },
  { name: "Social Sentiment", strategy: "Social Sentiment",    status: "offline", pnlToday: 0,   trades: 0,  winRate: 0,  capital: 5000,  color: "#a855f7", icon: "💬" },
];

export default function AgentFleet() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="rounded-xl p-3"
      style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
    >
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-text-primary">🤖</span>
          <span className="text-[10px] font-bold text-text-primary uppercase tracking-wider">Frota de Agentes IA</span>
        </div>
        <div className="flex items-center gap-2 text-[9px]">
          <span className="flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-neon-green" />{agents.filter(a => a.status === "online").length} ativos</span>
          <span className="text-text-dim">|</span>
          <span className="text-text-dim">{agents.length} total</span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2">
        {agents.map((agent, i) => (
          <motion.div
            key={agent.name}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-lg p-2.5 transition-all hover:scale-[1.02] cursor-pointer relative overflow-hidden group"
            style={{ background: "#050816", border: `1px solid ${agent.color}25` }}
          >
            {/* Glow on hover */}
            <div
              className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{ background: `radial-gradient(ellipse at top right, ${agent.color}10, transparent 60%)` }}
            />

            {/* Agent header */}
            <div className="flex items-center gap-2 mb-2 relative">
              <div
                className="w-6 h-6 rounded-md flex items-center justify-center text-xs"
                style={{ background: `${agent.color}20`, border: `1px solid ${agent.color}40`, color: agent.color }}
              >
                {agent.icon}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[10px] font-bold text-text-primary truncate">{agent.name}</div>
                <div className="text-[8px] text-text-dim truncate">{agent.strategy}</div>
              </div>
              <div className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${
                  agent.status === "online" ? "bg-neon-green shadow-[0_0_6px_#10b981]" :
                  agent.status === "idle" ? "bg-neon-amber" : "bg-text-dim"
                }`} />
              </div>
            </div>

            {/* Stats grid */}
            <div className="grid grid-cols-3 gap-1">
              <div>
                <div className="text-[7px] text-text-dim uppercase tracking-wider">Hoje</div>
                <div className={`text-[10px] font-bold font-mono ${agent.pnlToday >= 0 ? "text-neon-green" : "text-neon-red"}`}>
                  {agent.pnlToday >= 0 ? "+" : ""}${agent.pnlToday.toLocaleString()}
                </div>
              </div>
              <div>
                <div className="text-[7px] text-text-dim uppercase tracking-wider">Trades</div>
                <div className="text-[10px] font-bold font-mono text-text-primary">{agent.trades}</div>
              </div>
              <div>
                <div className="text-[7px] text-text-dim uppercase tracking-wider">Win</div>
                <div className="text-[10px] font-bold font-mono text-neon-green">{agent.winRate}%</div>
              </div>
            </div>

            {/* Capital bar */}
            <div className="mt-2 pt-1.5 border-t relative" style={{ borderColor: "#1a2a4a" }}>
              <div className="flex justify-between text-[8px]">
                <span className="text-text-dim">Capital</span>
                <span className="text-text-secondary font-mono">${agent.capital.toLocaleString()}</span>
              </div>
              <div className="h-1 rounded-full bg-border-primary mt-0.5 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${(agent.capital / 25000) * 100}%`, background: agent.color }}
                />
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}