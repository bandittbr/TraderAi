"use client";

import { useState, useCallback } from "react";
import { StrategyRanking }    from "@/components/strategies/StrategyRanking";
import { StrategyDetail }     from "@/components/strategies/StrategyDetail";
import { EvolutionPanel }     from "@/components/strategies/EvolutionPanel";
import { TopStrategiesPanel } from "@/components/strategies/TopStrategiesPanel";
import Link                   from "next/link";

export default function StrategiesPage() {
  const [selected, setSelected] = useState<number | null>(null);
  const [refresh,  setRefresh]  = useState(0);
  const onDone = useCallback(() => setRefresh((r) => r + 1), []);

  return (
    <div className="min-h-screen bg-[#0a0e1a]">

      {/* Navbar */}
      <nav className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M3 3v18h18"/>
                <path d="m19 9-5 5-4-4-3 3"/>
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-[#f9fafb]">TradeAI</span>
              <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono">
                Strategy Lab
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="text-xs text-[#9ca3af] hover:text-[#f9fafb] transition-colors">← Dashboard</Link>
            <Link href="/alpha" className="text-xs text-[#9ca3af] hover:text-[#f9fafb] transition-colors">Alpha →</Link>
            <Link href="/robustness" className="text-xs text-[#9ca3af] hover:text-[#f9fafb] transition-colors">Robustness →</Link>
          </div>
        </div>
      </nav>

      <main className="max-w-screen-xl mx-auto px-6 py-8 flex flex-col gap-6">

        <header>
          <h1 className="text-3xl font-bold text-[#f9fafb]">Strategy Evolution Engine</h1>
          <p className="text-sm text-[#9ca3af] mt-1">
            Laboratório Quantitativo · Descoberta Automática · Determinístico · Sem IA
          </p>
        </header>

        {/* Evolution Engine + Top 10 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <EvolutionPanel onDone={onDone} />
          <TopStrategiesPanel refresh={refresh} onSelect={setSelected} />
        </div>

        {/* Ranking + Detail */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <StrategyRanking onSelect={setSelected} refresh={refresh} />
          <StrategyDetail strategyId={selected} />
        </div>

        <footer className="text-center pt-4 border-t border-[#1f2937]">
          <p className="text-xs text-[#4b5563]">
            TradeAI v11.0.0 — Fase 11: Strategy Evolution Engine · Ranking Top 100.{" "}
            <Link href="/" className="text-blue-400 hover:text-blue-300 underline transition-colors">
              Dashboard →
            </Link>
            {" · "}
            <Link href="/alpha" className="text-blue-400 hover:text-blue-300 underline transition-colors">
              Alpha →
            </Link>
            {" · "}
            <Link href="/robustness" className="text-purple-400 hover:text-purple-300 underline transition-colors">
              Robustness →
            </Link>
          </p>
        </footer>
      </main>
    </div>
  );
}
