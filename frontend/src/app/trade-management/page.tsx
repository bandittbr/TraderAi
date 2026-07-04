"use client";

import Link from "next/link";
import ActiveTradesPanel   from "@/components/trade-management/ActiveTradesPanel";
import TrailingStopPanel   from "@/components/trade-management/TrailingStopPanel";
import BreakEvenPanel      from "@/components/trade-management/BreakEvenPanel";
import PartialTPPanel      from "@/components/trade-management/PartialTPPanel";
import ExitScoreMonitor    from "@/components/trade-management/ExitScoreMonitor";

export default function TradeManagementPage() {
  return (
    <div className="min-h-screen bg-[#0d1117] text-white">
      {/* Header */}
      <header className="border-b border-[#1f2937] px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">
              Trade Management Engine{" "}
              <span className="text-xs font-normal text-[#6b7280] ml-2">Fase 12</span>
            </h1>
            <p className="text-xs text-[#6b7280] mt-0.5">
              Time Stop · Break Even · Trailing Stop · Partial TP · Exit Score
            </p>
          </div>
          <Link href="/" className="text-xs text-[#6b7280] hover:text-white transition-colors">
            ← Dashboard
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-6 space-y-6">
        {/* Row 1: Active Trades (full width) */}
        <ActiveTradesPanel />

        {/* Row 2: Trailing + BreakEven */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TrailingStopPanel />
          <BreakEvenPanel />
        </div>

        {/* Row 3: Partial TP + Exit Score Monitor */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PartialTPPanel />
          <ExitScoreMonitor />
        </div>

        {/* Config reference */}
        <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-4">
          <h3 className="text-xs font-semibold text-[#9ca3af] mb-3">Configuração Ativa (Phase 12)</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {[
              { label: "Time Stop",      value: "48h" },
              { label: "Break Even",     value: "+1.5%" },
              { label: "Trailing Start", value: "+2%" },
              { label: "Trail Distance", value: "1%" },
              { label: "TP1 Parcial",    value: "+2% / 50%" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-[#0d1117] border border-[#1f2937] rounded-lg p-2 text-center">
                <div className="text-xs font-semibold text-white">{value}</div>
                <div className="text-[10px] text-[#6b7280] mt-0.5">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </main>

      <footer className="text-center pt-4 pb-6 border-t border-[#1f2937] mt-6">
        <p className="text-xs text-[#4b5563]">
          TradeAI v12.0.0 — Fase 12: Trade Management Engine{" "}
          <Link href="/paper-trading" className="text-amber-400 hover:text-amber-300 underline">
            Paper Trading →
          </Link>
        </p>
      </footer>
    </div>
  );
}
