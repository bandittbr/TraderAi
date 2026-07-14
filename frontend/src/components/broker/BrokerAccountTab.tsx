"use client";

import { useState } from "react";
import { getBrokerBalance, getBrokerPositions, getBrokerOpenOrders } from "@/lib/api";
import type { BrokerPosition, BrokerOrderResponse, BrokerBalance, BrokerStatusResponse } from "@/types";

interface BrokerAccountTabProps {
  status: BrokerStatusResponse | null;
  onRefresh: () => Promise<void>;
}

export default function BrokerAccountTab({ status, onRefresh }: BrokerAccountTabProps) {
  const [balances, setBalances] = useState<BrokerBalance[]>([]);
  const [positions, setPositions] = useState<BrokerPosition[]>([]);
  const [openOrders, setOpenOrders] = useState<BrokerOrderResponse[]>([]);
  const [loading, setLoading] = useState(false);

  function formatNumber(n: number, decimals = 4): string {
    return n.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  }

  async function loadData() {
    setLoading(true);
    try {
      const [bal, pos, ord] = await Promise.all([
        getBrokerBalance(),
        getBrokerPositions(),
        getBrokerOpenOrders(),
      ]);
      if (bal) setBalances(bal.balances.filter((b) => b.total > 0).sort((a, b) => b.total - a.total));
      if (pos) setPositions(pos.positions);
      if (ord) setOpenOrders(ord.orders);
    } catch (e) {
      console.error("Failed to load account data:", e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Balances */}
      <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
        <div className="p-4 border-b border-[#1f2937] flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">Saldos da Conta</h3>
          <span className="px-3 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full">
            {balances.length} ativos
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-[#4b5563] border-b border-[#1f2937]">
                <th className="p-3">Ativo</th>
                <th className="p-3">Livre</th>
                <th className="p-3">Bloqueado</th>
                <th className="p-3">Total</th>
                <th className="p-3">≈ USDT</th>
              </tr>
            </thead>
            <tbody>
              {balances
                .filter((b) => b.total > 0)
                .sort((a, b) => b.total - a.total)
                .map((bal) => (
                  <tr key={bal.asset} className="border-b border-[#1f2937] hover:bg-[#0a0e1a]">
                    <td className="p-3 font-bold text-white">{bal.asset}</td>
                    <td className="p-3 font-mono text-[#9ca3af]">{bal.free.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                    <td className="p-3 font-mono text-[#6b7280]">{bal.locked.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                    <td className="p-3 font-mono text-white">{bal.total.toLocaleString("en-US", { minimumFractionDigits: 6, maximumFractionDigits: 6 })}</td>
                    <td className="p-3 font-mono text-[#9ca3af]">
                      {bal.asset === "USDT" ? bal.total.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Account Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <div className="text-xs text-[#4b5563] uppercase tracking-wider mb-1">Modo</div>
          <div className={`text-lg font-bold ${status?.auto_mode ? "text-emerald-400" : "text-amber-400"}`}>
            {status?.auto_mode ? "AUTO" : "MANUAL"}
          </div>
        </div>
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <div className="text-xs text-[#4b5563] uppercase tracking-wider mb-1">Agente</div>
          <div className="text-lg font-bold text-blue-400">{status?.selected_agent?.toUpperCase() || "—"}</div>
        </div>
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-6">
          <div className="text-xs text-[#4b5563] uppercase tracking-wider mb-1">Rede</div>
          <div className={`text-lg font-bold ${status?.testnet ? "text-amber-400" : "text-red-400"}`}>
            {status?.testnet ? "TESTNET" : "MAINNET"}
          </div>
        </div>
      </div>
    </div>
  );
}