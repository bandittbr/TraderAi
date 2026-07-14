"use client";

import { useState } from "react";
import { getBrokerPositions, placeBrokerOrder } from "@/lib/api";
import type { BrokerPosition, OrderSide, OrderType, PositionSide } from "@/types";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT", "LINKUSDT"];

interface BrokerPositionsTabProps {
  positions: BrokerPosition[];
  onRefresh: () => Promise<void>;
}

export default function BrokerPositionsTab({ positions, onRefresh }: BrokerPositionsTabProps) {
  const [closingPosition, setClosingPosition] = useState<string | null>(null);

  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  function pnlColor(pnl: number): string {
    return pnl >= 0 ? "text-emerald-400" : "text-red-400";
  }

  async function handleClosePosition(pos: BrokerPosition) {
    setClosingPosition(pos.symbol);
    try {
      const side = pos.position_side === "LONG" ? "SELL" : "BUY";
      await fetch(`/api/v1/broker/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol: pos.symbol,
          side,
          order_type: "MARKET",
          quantity: pos.size,
          position_side: pos.position_side,
          reduce_only: true,
        }),
      });
      await onRefresh();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setClosingPosition(null);
    }
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div className="p-4 border-b border-[#1f2937] flex items-center justify-between">
        <h3 className="text-lg font-bold text-white">Posições Abertas</h3>
        <span className="px-3 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full">
          {positions.length} posição{positions.length !== 1 ? "ões" : ""}
        </span>
      </div>
      {positions.length === 0 ? (
        <div className="p-12 text-center text-[#4b5563]">
          <div className="text-4xl mb-2">📊</div>
          <p>Nenhuma posição aberta</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-[#4b5563] border-b border-[#1f2937]">
                <th className="p-3">Símbolo</th>
                <th className="p-3">Lado</th>
                <th className="p-3">Tamanho</th>
                <th className="p-3">Entrada</th>
                <th className="p-3">Marca</th>
                <th className="p-3">PnL Não Real.</th>
                <th className="p-3">Alav.</th>
                <th className="p-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {positions.map(pos => (
                <tr key={pos.symbol} className="border-b border-[#1f2937] hover:bg-[#0a0e1a]">
                  <td className="p-3 font-mono text-white">{pos.symbol}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      pos.position_side === "LONG" ? "bg-emerald-500/20 text-emerald-400" :
                      pos.position_side === "SHORT" ? "bg-red-500/20 text-red-400" :
                      "bg-blue-500/20 text-blue-400"
                    }`}>
                      {pos.position_side}
                    </span>
                  </td>
                  <td className="p-3 font-mono text-white">{pos.size.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                  <td className="p-3 font-mono text-[#9ca3af]">${pos.entry_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="p-3 font-mono text-white">${pos.mark_price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                  <td className="p-3 font-mono font-bold {pnlColor(pos.unrealized_pnl)}">
                    ${pos.unrealized_pnl.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="p-3 text-[#9ca3af]">{pos.leverage}x</td>
                  <td className="p-3">
                    <button
                      onClick={() => handleClosePosition(pos)}
                      disabled={closingPosition === pos.symbol}
                      className="px-3 py-1 text-xs rounded bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-colors disabled:opacity-50"
                    >
                      Fechar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}