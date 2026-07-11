"use client";
import { useState } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AgentChart } from "@/components/dashboard/AgentChart";
import ScalperAccount from "@/components/scalper/ScalperAccount";
import ScalperRisk    from "@/components/scalper/ScalperRisk";
import ScalperStats   from "@/components/scalper/ScalperStats";
import ScalperTrades  from "@/components/scalper/ScalperTrades";
import ScalperSignals from "@/components/scalper/ScalperSignals";

export default function ScalperPage() {
  const { prices } = useWebSocket();
  const [days, setDays] = useState(30);

  return (
    <div className="p-6 space-y-5 max-w-[1400px] mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Scalper Engine</h1>
          <p className="text-[11px] text-[#3d5a80] mt-0.5">
            Multi-Timeframe · 1m / 5m / 15m · BTCUSDT ETHUSDT SOLUSDT AVAXUSDT · Paper Trading
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex gap-1">
            {[7, 14, 30].map(d => (
              <button key={d} onClick={() => setDays(d)}
                className="text-[11px] px-2.5 py-1 rounded-lg transition-all"
                style={{
                  background: days === d ? "#1e3a5f" : "#0d1525",
                  color:      days === d ? "#60a5fa" : "#3d5a80",
                  border:     "1px solid " + (days === d ? "#2563eb" : "#141c2e"),
                }}>
                {d}d
              </button>
            ))}
          </div>
          <div className="text-[10px] px-2.5 py-1 rounded-lg font-mono"
            style={{ background: "#0d1525", color: "#7c3aed", border: "1px solid #2e1065" }}>
            MTF: 15m → 5m → 1m
          </div>
        </div>
      </div>

      {/* Linha 1: Conta + Risk */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <ScalperAccount />
        </div>
        <div>
          <ScalperRisk />
        </div>
      </div>

      {/* Gráfico com markers de trade em tempo real */}
      <AgentChart
        agent="scalper"
        symbol="BTCUSDT"
        livePrice={prices["BTCUSDT"]}
        height={350}
      />

      {/* Linha 2: Stats */}
      <ScalperStats days={days} />

      {/* Linha 3: Trades */}
      <ScalperTrades />

      {/* Linha 4: Sinais */}
      <ScalperSignals />

      {/* Rodapé de parâmetros */}
      <div className="rounded-xl p-4" style={{ background: "#0d1525", border: "1px solid #141c2e" }}>
        <div className="text-[10px] text-[#3d5a80] uppercase tracking-widest mb-3">Parâmetros Ativos</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
          {[
            { label: "Stop Loss",       value: "0.25%" },
            { label: "Take Profit",     value: "0.50%" },
            { label: "Break Even",      value: "+0.20%" },
            { label: "Trailing Ativa",  value: "+0.40%" },
            { label: "Trailing Dist",   value: "0.15%" },
            { label: "Risco/Trade",     value: "$10" },
            { label: "Consec. Losses",  value: "5 max" },
            { label: "Daily Loss Max",  value: "3.0%" },
            { label: "Time Stop",       value: "120min" },
            { label: "Ativos",          value: "4 pares" },
            { label: "Timeframes",      value: "1m 5m 15m" },
            { label: "Modo",            value: "Paper" },
          ].map(({ label, value }) => (
            <div key={label} className="text-center">
              <div className="text-white font-mono text-sm font-bold">{value}</div>
              <div className="text-[9px] text-[#2d4060] uppercase tracking-widest mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
