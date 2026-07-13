"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AgentChart } from "./AgentChart";
import { useWebSocket } from "@/hooks/useWebSocket";

interface AgentEntry {
  name: string;
  status: string;
  win_rate: number;
  profit_factor: number;
  total_pnl_pct: number;
  total_trades: number;
  net_win_rate: number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  best: boolean;
}

interface Leaderboard {
  agents: AgentEntry[];
}

const AGENT_LINKS: Record<string, string> = {
  Worker:  "/worker",
  Scalper: "/scalper",
  Paper:   "/paper-trading",
  Groq:    "/groq",
};

const AGENT_COLORS: Record<string, string> = {
  Worker:  "#7c3aed",  // purple
  Scalper: "#f59e0b",  // amber
  Paper:   "#2563eb",  // blue
  Groq:    "#8b5cf6",  // violet
};

export default function AgentesAI() {
  const [data, setData] = useState<Leaderboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const res = await fetch("/api/v1/agents/leaderboard?days=30");
        if (res.ok) setData(await res.json());
      } catch (e) {
        console.error("[AgentesAI] fetch error:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchLeaderboard();
    const interval = setInterval(fetchLeaderboard, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl bg-[#0a1020] border border-[#141c2e] p-5">
        <div className="text-xs text-[#4a6080] animate-pulse">Carregando agentes...</div>
      </div>
    );
  }

  const { prices } = useWebSocket();
  const [selectedAgent, setSelectedAgent] = useState<string>("paper");

  const agents = data?.agents ?? [];
  const best = agents.find((a) => a.best);

  const agentMap = agents.reduce((acc, a) => ({ ...acc, [a.name.toLowerCase()]: a }), {} as Record<string, AgentEntry>);

  return (
    <div className="rounded-xl bg-[#0a1020] border border-[#141c2e] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#141c2e]">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-[10px] font-bold text-white">
            AI
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">AGENTES AI</h2>
            <p className="text-[9px] text-[#4a6080] tracking-wide">
              {best ? `Melhor: ${best.name} (PF ${best.net_profit_factor.toFixed(2)})` : "Comparativo de performance"}
            </p>
          </div>
        </div>
        <Link
          href="/worker"
          className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
        >
          Detalhes →
        </Link>
      </div>

      {/* Grid de agentes */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4">
        {agents.map((agent) => {
          const color = AGENT_COLORS[agent.name] || "#4a6080";
          const pnlPositive = agent.total_net_pnl_pct >= 0;
          const wrGood = agent.net_win_rate >= 50;
          const agentKey = agent.name.toLowerCase();

          return (
            <button
              key={agent.name}
              onClick={() => setSelectedAgent(agentKey)}
              className={`block rounded-lg p-4 transition-all hover:scale-[1.02] border text-left ${
                selectedAgent === agentKey
                  ? "bg-gradient-to-br from-purple-900/20 to-blue-900/20 border-purple-500/40 ring-1 ring-purple-500/20"
                  : agent.best
                  ? "bg-gradient-to-br from-purple-900/20 to-blue-900/20 border-purple-500/30"
                  : "bg-[#060c18] border-[#141c2e] hover:border-[#2a3a5a]"
              }`}
            >
              {/* Nome + Status */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-sm font-bold text-white">{agent.name}</span>
                </div>
                <span className={`text-[9px] px-1.5 py-0.5 rounded-full ${
                  agent.status === "running"
                    ? "bg-emerald-900/30 text-emerald-400"
                    : "bg-[#141c2e] text-[#4a6080]"
                }`}>
                  {agent.status}
                </span>
              </div>

              {/* Métricas principais */}
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div>
                  <span className="text-[#4a6080]">Win Rate</span>
                  <div className={`font-bold ${wrGood ? "text-emerald-400" : "text-red-400"}`}>
                    {agent.net_win_rate.toFixed(1)}%
                  </div>
                </div>
                <div>
                  <span className="text-[#4a6080]">P. Factor</span>
                  <div className={`font-bold ${
                    agent.net_profit_factor >= 1.5 ? "text-emerald-400" :
                    agent.net_profit_factor >= 1 ? "text-amber-400" : "text-red-400"
                  }`}>
                    {agent.net_profit_factor.toFixed(2)}
                  </div>
                </div>
                <div>
                  <span className="text-[#4a6080]">PnL (Net)</span>
                  <div className={`font-bold ${pnlPositive ? "text-emerald-400" : "text-red-400"}`}>
                    {pnlPositive ? "+" : ""}{agent.total_net_pnl_pct.toFixed(2)}%
                  </div>
                </div>
                <div>
                  <span className="text-[#4a6080]">Trades</span>
                  <div className="font-bold text-white">{agent.total_trades}</div>
                </div>
              </div>

              {/* Badge de melhor agente */}
              {agent.best && (
                <div className="mt-2 text-[9px] text-purple-400 font-semibold tracking-wider">
                  MELHOR AGENTE
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* AgentChart — gráfico com markers de trade em tempo real */}
      <div className="px-4 pb-4">
        <AgentChart
          agent={selectedAgent}
          symbol="BTCUSDT"
          livePrice={prices["BTCUSDT"]}
        />
      </div>
    </div>
  );
}
