"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface AgentInfo {
  name: string;
  description: string;
  enabled: boolean;
  last_execution: string | null;
}

interface AgentAccount {
  agent_name: string;
  balance: number;
  initial_balance: number;
  peak_balance: number;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  enabled: boolean;
  updated_at: string | null;
}

interface AgentTrade {
  id: number;
  agent_name: string;
  symbol: string;
  trade_side: string;
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  leverage: number;
  pnl: number | null;
  pnl_pct: number | null;
  net_pnl_pct: number | null;
  status: string;
  close_reason: string | null;
  opened_at: string;
  closed_at: string | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
}

interface LeaderboardEntry {
  name: string;
  status: string;
  win_rate: number;
  profit_factor: number;
  total_pnl_pct: number;
  total_trades: number;
  net_win_rate: number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  balance: number;
  best: boolean;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

async function fetchJSON<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function formatPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function formatUSD(v: number | null | undefined): string {
  if (v == null) return "—";
  return `$${v.toFixed(2)}`;
}

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("pt-BR", { timeZone: "UTC" });
}

// ── Componentes ────────────────────────────────────────────────────────────────

function AgentCard({
  agent,
  account,
  trades,
  onToggle,
}: {
  agent: AgentInfo;
  account: AgentAccount | null;
  trades: AgentTrade[];
  onToggle: (name: string, enable: boolean) => void;
}) {
  const openTrades = trades.filter((t) => t.status === "OPEN");
  const closedTrades = trades.filter((t) => t.status === "CLOSED");
  const wins = closedTrades.filter((t) => (t.net_pnl_pct ?? 0) > 0);
  const losses = closedTrades.filter((t) => (t.net_pnl_pct ?? 0) <= 0);
  const wr = closedTrades.length > 0 ? (wins.length / closedTrades.length) * 100 : 0;
  const totalPnl = closedTrades.reduce((s, t) => s + (t.net_pnl_pct ?? 0), 0);

  return (
    <div
      className="rounded-xl border p-4 transition-all"
      style={{
        background: agent.enabled ? "#0b1424" : "#080c14",
        borderColor: agent.enabled ? "#1e3050" : "#141c2e",
        opacity: agent.enabled ? 1 : 0.6,
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-white font-bold text-sm">{agent.name}</h3>
            <span
              className={`w-2 h-2 rounded-full ${
                agent.enabled ? "bg-green-500" : "bg-gray-600"
              }`}
            />
          </div>
          <p className="text-[#4a6080] text-xs mt-0.5">{agent.description}</p>
        </div>
        <button
          onClick={() => onToggle(agent.name, !agent.enabled)}
          className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
            agent.enabled
              ? "bg-red-600/20 text-red-400 hover:bg-red-600/30"
              : "bg-green-600/20 text-green-400 hover:bg-green-600/30"
          }`}
        >
          {agent.enabled ? "Desativar" : "Ativar"}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        <div className="bg-[#0a1020] rounded-lg p-2">
          <div className="text-[9px] text-[#3b4a6b] uppercase tracking-wider">Saldo</div>
          <div className="text-white text-sm font-mono mt-0.5">
            {account ? formatUSD(account.balance) : "—"}
          </div>
        </div>
        <div className="bg-[#0a1020] rounded-lg p-2">
          <div className="text-[9px] text-[#3b4a6b] uppercase tracking-wider">P&L Total</div>
          <div
            className={`text-sm font-mono mt-0.5 ${
              totalPnl >= 0 ? "text-green-400" : "text-red-400"
            }`}
          >
            {formatPct(totalPnl)}
          </div>
        </div>
        <div className="bg-[#0a1020] rounded-lg p-2">
          <div className="text-[9px] text-[#3b4a6b] uppercase tracking-wider">Win Rate</div>
          <div className="text-white text-sm font-mono mt-0.5">{wr.toFixed(1)}%</div>
        </div>
        <div className="bg-[#0a1020] rounded-lg p-2">
          <div className="text-[9px]X text-[#3b4a6b] uppercase tracking-wider">Trades</div>
          <div className="text-white text-sm font-mono mt-0.5">{closedTrades.length}</div>
        </div>
      </div>

      {/* Open Trades */}
      {openTrades.length > 0 && (
        <div className="mt-2">
          <div className="text-[10px] text-[#3b4a6b] uppercase tracking-wider mb-1">
            Trades Abertos ({openTrades.length})
          </div>
          {openTrades.slice(0, 3).map((t) => (
            <div
              key={t.id}
              className="flex items-center justify-between bg-[#0a1020] rounded px-2 py-1.5 mb-1 text-xs"
            >
              <span className="text-white font-mono">
                {t.symbol} {t.trade_side}
              </span>
              <span className="text-[#4a6080] font-mono">
                @ {t.entry_price.toFixed(2)}
              </span>
              <span
                className={`font-mono ${
                  (t.unrealized_pnl_pct ?? 0) >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {formatPct(t.unrealized_pnl_pct)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LeaderboardTable({ entries }: { entries: LeaderboardEntry[] }) {
  const sorted = [...entries].sort((a, b) => b.total_net_pnl_pct - a.total_net_pnl_pct);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[#3b4a6b] uppercase tracking-wider border-b border-[#141c2e]">
            <th className="text-left py-2 px-2">#</th>
            <th className="text-left py-2 px-2">Agente</th>
            <th className="text-right py-2 px-2">Status</th>
            <th className="text-right py-2 px-2">Saldo</th>
            <th className="text-right py-2 px-2">P&L %</th>
            <th className="text-right py-2 px-2">Win Rate</th>
            <th className="text-right py-2 px-2">Profit Factor</th>
            <th className="text-right py-2 px-2">Trades</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((e, i) => (
            <tr
              key={e.name}
              className={`border-b border-[#0f1a2e] hover:bg-[#0a1020] transition-all ${
                e.best ? "bg-green-900/10" : ""
              }`}
            >
              <td className="py-2 px-2 text-[#4a6080] font-mono">{i + 1}</td>
              <td className="py-2 px-2">
                <span className="text-white font-medium">{e.name}</span>
                {e.best && (
                  <span className="ml-2 text-[9px] bg-green-600/20 text-green-400 px-1.5 py-0.5 rounded">
                    BEST
                  </span>
                )}
              </td>
              <td className="py-2 px-2 text-right">
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded ${
                    e.status === "running"
                      ? "bg-green-600/20 text-green-400"
                      : e.status === "paused"
                      ? "bg-yellow-600/20 text-yellow-400"
                      : "bg-gray-600/20 text-gray-400"
                  }`}
                >
                  {e.status}
                </span>
              </td>
              <td className="py-2 px-2 text-right text-white font-mono">
                {formatUSD(e.balance)}
              </td>
              <td
                className={`py-2 px-2 text-right font-mono ${
                  e.total_net_pnl_pct >= 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {formatPct(e.total_net_pnl_pct)}
              </td>
              <td className="py-2 px-2 text-right text-white font-mono">
                {e.win_rate.toFixed(1)}%
              </td>
              <td className="py-2 px-2 text-right text-white font-mono">
                {e.profit_factor.toFixed(2)}
              </td>
              <td className="py-2 px-2 text-right text-[#4a6080] font-mono">
                {e.total_trades}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [accounts, setAccounts] = useState<Record<string, AgentAccount>>({});
  const [trades, setTrades] = useState<AgentTrade[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

  const loadData = async () => {
    const agentsData = await fetchJSON<{ agents: AgentInfo[] }>("/agents");
    if (!agentsData) return;
    setAgents(agentsData.agents);

    // Load accounts and trades for each agent
    const accs: Record<string, AgentAccount> = {};
    let allTrades: AgentTrade[] = [];
    for (const a of agentsData.agents) {
      const acc = await fetchJSON<AgentAccount>(`/agents/${encodeURIComponent(a.name)}/account`);
      if (acc) accs[a.name] = acc;
      const ts = await fetchJSON<AgentTrade[]>(
        `/agents/${encodeURIComponent(a.name)}/trades?limit=20`
      );
      if (ts) allTrades = allTrades.concat(ts);
    }
    setAccounts(accs);
    setTrades(allTrades);

    const lb = await fetchJSON<{ agents: LeaderboardEntry[] }>("/agents/leaderboard");
    if (lb) setLeaderboard(lb.agents);
  };

  useEffect(() => {
    loadData().finally(() => setLoading(false));
    const interval = setInterval(loadData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleToggle = async (name: string, enable: boolean) => {
    const action = enable ? "enable" : "disable";
    await fetch(`${API_BASE}/agents/${encodeURIComponent(name)}/${action}`, {
      method: "POST",
    });
    loadData();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-[#4a6080] text-sm">Carregando agentes...</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-white">Multi-Agent Trading System</h1>
        <p className="text-sm text-[#4a6080] mt-1">
          10 agentes de trading com estratégias diferentes, cada um com $100.000 simulados
        </p>
      </div>

      {/* Leaderboard */}
      <div className="rounded-xl border border-[#1e3050] bg-[#0b1424] p-4 mb-6">
        <h2 className="text-white font-bold text-sm mb-3">Leaderboard</h2>
        {leaderboard.length > 0 ? (
          <LeaderboardTable entries={leaderboard} />
        ) : (
          <div className="text-[#4a6080] text-xs py-4 text-center">
            Nenhum trade fechado ainda. Os agentes começam a operar no próximo ciclo de indicadores.
          </div>
        )}
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <AgentCard
            key={agent.name}
            agent={agent}
            account={accounts[agent.name] ?? null}
            trades={trades.filter((t) => t.agent_name === agent.name)}
            onToggle={handleToggle}
          />
        ))}
      </div>
    </div>
  );
}
