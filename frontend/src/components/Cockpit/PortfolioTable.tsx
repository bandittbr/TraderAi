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
      style={{ background: "#080c14", border: "1px solid #1a2540" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1a2540]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-white">💼</span>
          <span className="text-[10px] font-bold text-white uppercase tracking-wider">Portfólio — Posições Abertas</span>
        </div>
        <div className="flex items-center gap-3 text-[9px]">
          <span className="text-[#2d4060]">Exposição: <span className="text-white font-mono">$84,250</span></span>
          <span className="text-[#2d4060]">Risco: <span className="text-amber-400 font-mono">2.4%</span></span>
          <span className="text-emerald-400 font-mono font-bold">+$2,847.50</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[10px]">
          <thead>
            <tr className="border-b border-[#1a2540]">
              {["Ativo", "Direção", "Entrada", "Atual", "P&L", "Alav.", "Size", "Agente"].map(h => (
                <th key={h} className="px-3 py-2 text-left text-[8px] text-[#2d4060] uppercase tracking-wider font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map((p, i) => {
              const pnlColor = p.pnlPct >= 0 ? "text-emerald-400" : "text-red-400";
              return (
                <motion.tr
                  key={p.asset + p.direction}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="border-b border-[#141c2e] hover:bg-[#0a0e1a40] transition-colors"
                >
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white">{p.asset}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={`px-1.5 py-0.5 rounded-full text-[8px] font-bold ${
                      p.direction === "LONG" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}>
                      {p.direction}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[#8aa4c8]">${p.entry.toLocaleString()}</td>
                  <td className="px-3 py-2.5 font-mono text-white">${p.current.toLocaleString()}</td>
                  <td className={`px-3 py-2.5 font-mono font-bold ${pnlColor}`}>
                    {p.pnlPct >= 0 ? "+" : ""}{p.pnlPct.toFixed(2)}%
                  </td>
                  <td className="px-3 py-2.5 font-mono text-[#2d4060]">{p.leverage}x</td>
                  <td className="px-3 py-2.5 font-mono text-[#2d4060]">{p.size}</td>
                  <td className="px-3 py-2.5">
                    <span className="text-[9px] text-[#8aa4c8]">{p.agent}</span>
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
