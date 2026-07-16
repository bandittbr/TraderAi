"use client";

import { motion } from "framer-motion";

interface Position {
  asset: string;
  direction: "LONG" | "SHORT";
  entry: number;
  current: number;
  pnlPct: number;
  agent: string;
  leverage: number;
  size: number;
}

const positions: Position[] = [
  { asset: "BTC",  direction: "LONG",  entry: 64200, current: 64850, pnlPct: 3.04, agent: "Scalper Pro",     leverage: 3, size: 0.5 },
  { asset: "ETH",  direction: "LONG",  entry: 3380,  current: 3452,  pnlPct: 2.13, agent: "Trend Follower",  leverage: 2, size: 5.0 },
  { asset: "SOL",  direction: "SHORT", entry: 145,   current: 142,   pnlPct: 2.07, agent: "Breakout Hunter", leverage: 2, size: 20 },
  { asset: "ADA",  direction: "LONG",  entry: 0.44,  current: 0.45,  pnlPct: 2.27, agent: "Momentum RSI",    leverage: 1, size: 1000 },
  { asset: "LINK", direction: "SHORT", entry: 14.5,  current: 14.2,  pnlPct: 2.07, agent: "Reversal Master", leverage: 2, size: 50 },
];

export default function PortfolioTable() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.35 }}
      className="rounded-xl overflow-hidden"
      style={{ background: "#0a0f1e", border: "1px solid #1a2a4a" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b" style={{ borderColor: "#1a2a4a" }}>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-text-primary">💼</span>
          <span className="text-[10px] font-bold text-text-primary uppercase tracking-wider">Portfólio — Posições Abertas</span>
        </div>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="text-text-dim">Exposição: <span className="text-text-primary font-mono">$84,250</span></span>
          <span className="text-text-dim">Risco: <span className="text-neon-amber font-mono">2.4%</span></span>
          <span className="text-neon-green font-mono font-bold">+$2,847.50</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] cockpit-table">
          <thead>
            <tr className="border-b" style={{ borderColor: "#1a2a4a" }}>
              {["Ativo", "Direção", "Entrada", "Atual", "P&L", "Alav.", "Size", "Agente"].map(h => (
                <th key={h} className="px-3 py-2 text-left text-[8px] text-text-dim uppercase tracking-wider font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((p, i) => {
              const pnlColor = p.pnlPct >= 0 ? "text-neon-green" : "text-neon-red";
              return (
                <motion.tr
                  key={p.asset + p.direction}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b hover:bg-white/2 transition-colors"
                  style={{ borderColor: "#141c2e" }}
                >
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-text-primary">{p.asset}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold ${
                      p.direction === "LONG"
                        ? "bg-neon-green/10 text-neon-green border border-neon-green/20"
                        : "bg-neon-red/10 text-neon-red border border-neon-red/20"
                    }`}>
                      {p.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-text-dim">${p.entry.toLocaleString()}</td>
                  <td className="px-3 py-2.5 font-mono text-text-primary">${p.current.toLocaleString()}</td>
                  <td className={`px-3 py-2.5 font-mono font-bold ${pnlColor}`}>
                    {p.pnlPct >= 0 ? "+" : ""}{p.pnlPct.toFixed(2)}%
                  </td>
                  <td className="px-3 py-2.5 font-mono text-text-dim">{p.leverage}x</td>
                  <td className="px-3 py-2.5 font-mono text-text-dim">{p.size}</td>
                  <td className="px-3 py-2.5">
                    <span className="text-[9px] text-text-dim">{p.agent}</span>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}