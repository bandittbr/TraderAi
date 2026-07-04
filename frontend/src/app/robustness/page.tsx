"use client";

import { useState, useCallback } from "react";
import { RobustnessScore }  from "@/components/robustness/RobustnessScore";
import { WalkForwardChart } from "@/components/robustness/WalkForwardChart";
import { MonteCarloPanel }  from "@/components/robustness/MonteCarloPanel";
import { StabilityRanking } from "@/components/robustness/StabilityRanking";
import { RiskOfRuin }       from "@/components/robustness/RiskOfRuin";
import Link                 from "next/link";

export default function RobustnessPage() {
  const [refresh, setRefresh] = useState(0);
  const onRun = useCallback(() => setRefresh((r) => r + 1), []);

  return (
    <div className="min-h-screen bg-[#0a0e1a]">

      {/* Navbar */}
      <nav className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-500 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-[#f9fafb]">TradeAI</span>
              <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-mono">
                Robustness
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="text-xs text-[#9ca3af] hover:text-[#f9fafb] transition-colors">
              ← Dashboard
            </Link>
            <Link href="/alpha" className="text-xs text-[#9ca3af] hover:text-[#f9fafb] transition-colors">
              Alpha →
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-screen-xl mx-auto px-6 py-8 flex flex-col gap-6">

        <header>
          <h1 className="text-3xl font-bold text-[#f9fafb]">Walk Forward Validation Engine</h1>
          <p className="text-sm text-[#9ca3af] mt-1">
            Robustez estatística · Determinístico · Auditável · Reprodutível
          </p>
        </header>

        {/* Score principal + Walk Forward */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <RobustnessScore onRun={onRun} />
          <WalkForwardChart refresh={refresh} />
        </div>

        {/* Monte Carlo + Risco de Ruína */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MonteCarloPanel refresh={refresh} />
          <RiskOfRuin refresh={refresh} />
        </div>

        {/* Estabilidade por dimensão (full width) */}
        <StabilityRanking refresh={refresh} />

        <footer className="text-center pt-4 border-t border-[#1f2937]">
          <p className="text-xs text-[#4b5563]">
            TradeAI v10.0.0 — Fase 10: Walk Forward · Monte Carlo · Strategy Stability.{" "}
            <Link href="/" className="text-blue-400 hover:text-blue-300 underline transition-colors">
              Dashboard →
            </Link>
            {" · "}
            <Link href="/alpha" className="text-purple-400 hover:text-purple-300 underline transition-colors">
              Alpha Discovery →
            </Link>
          </p>
        </footer>
      </main>
    </div>
  );
}
