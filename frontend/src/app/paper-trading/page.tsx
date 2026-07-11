/**
 * TradeAI - Página: Paper Trading (Fase 4)
 * Validação de sinais com conta virtual — sem risco real.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AgentChart } from "@/components/dashboard/AgentChart";
import {
  getPaperAccount,
  getPaperStats,
  getPaperTrades,
} from "@/lib/api";
import type {
  PaperAccountResponse,
  PaperStatsResponse,
  PaperTradeResponse,
} from "@/types";
import { PaperAccountCard }  from "@/components/paper-trading/PaperAccountCard";
import { PaperStatsGrid }    from "@/components/paper-trading/PaperStatsGrid";
import { TradesTable }       from "@/components/paper-trading/TradesTable";
import { BacktestPanel }     from "@/components/paper-trading/BacktestPanel";

const POLL_INTERVAL_MS = 30_000;

type TradeFilter = "ALL" | "OPEN" | "CLOSED";

export default function PaperTradingPage() {
  const { prices } = useWebSocket();
  const [account,  setAccount]  = useState<PaperAccountResponse | null>(null);
  const [stats,    setStats]    = useState<PaperStatsResponse | null>(null);
  const [trades,   setTrades]   = useState<PaperTradeResponse[]>([]);
  const [filter,   setFilter]   = useState<TradeFilter>("ALL");
  const [loading,  setLoading]  = useState(true);

  const refresh = useCallback(async () => {
    const [acc, st, tr] = await Promise.all([
      getPaperAccount(),
      getPaperStats(),
      getPaperTrades("ALL", 100),
    ]);
    setAccount(acc);
    setStats(st);
    setTrades(tr);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const filteredTrades = filter === "ALL"
    ? trades
    : trades.filter((t) => t.status === filter);

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-[#f9fafb]">
      {/* Navbar */}
      <header className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-[#60a5fa] hover:text-blue-300 text-sm font-medium transition-colors">
              ← Dashboard
            </Link>
            <span className="text-[#1f2937]">|</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-sm font-bold text-[#f9fafb]">Paper Trading</span>
            </div>
          </div>
          <button
            onClick={refresh}
            className="text-xs text-[#6b7280] hover:text-[#f9fafb] transition-colors px-2 py-1 rounded border border-[#1f2937] hover:border-[#374151]"
          >
            Atualizar
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Aviso de simulação */}
        <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 flex items-start gap-3">
          <span className="text-amber-400 text-base mt-0.5">⚠</span>
          <div>
            <p className="text-sm font-semibold text-amber-400">Modo Simulação</p>
            <p className="text-xs text-[#6b7280] mt-0.5">
              Todas as operações são virtuais. Nenhum ativo real é comprado ou vendido.
              O objetivo é validar a qualidade dos sinais antes de operar com capital real.
            </p>
          </div>
        </div>

        {/* Conta + Performance */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PaperAccountCard account={account} loading={loading} />
          <PaperStatsGrid   stats={stats}     loading={loading} />
        </div>

        {/* Gráfico com markers de trade em tempo real */}
        <AgentChart
          agent="paper"
          symbol="BTCUSDT"
          livePrice={prices["BTCUSDT"]}
          height={350}
        />

        {/* Tabela de trades */}
        <div>
          {/* Filtros */}
          <div className="flex gap-2 mb-3">
            {(["ALL", "OPEN", "CLOSED"] as TradeFilter[]).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-colors border ${
                  filter === f
                    ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                    : "bg-[#111827] text-[#6b7280] border-[#1f2937] hover:text-[#f9fafb]"
                }`}
              >
                {f === "ALL" ? "Todos" : f === "OPEN" ? "Abertos" : "Fechados"}
                {f !== "ALL" && (
                  <span className="ml-1 text-[10px] text-[#4b5563]">
                    ({f === "OPEN"
                      ? trades.filter((t) => t.status === "OPEN").length
                      : trades.filter((t) => t.status === "CLOSED").length})
                  </span>
                )}
              </button>
            ))}
          </div>
          <TradesTable trades={filteredTrades} loading={loading} />
        </div>

        {/* Backtest */}
        <BacktestPanel />
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1f2937] mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <p className="text-xs text-center text-[#4b5563]">
            TradeAI · Paper Trading · Validação de Sinais · Sem risco real
          </p>
        </div>
      </footer>
    </div>
  );
}
