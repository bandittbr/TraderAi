/**
 * TradeAI — Fase 9: Alpha Discovery Engine
 * Página /alpha — ranking de setups, fatores de risco, meta-analytics,
 * setup quality score e heatmap de performance.
 */
"use client";

import Link from "next/link";
import { BestSetups }         from "@/components/alpha/BestSetups";
import { WorstSetups }        from "@/components/alpha/WorstSetups";
import { MetaAnalytics }      from "@/components/alpha/MetaAnalytics";
import { SetupQualityPanel }  from "@/components/alpha/SetupQualityPanel";
import { AlphaHeatmap }       from "@/components/alpha/AlphaHeatmap";
import { API_BASE }           from "@/lib/api";
import { useState }           from "react";

function RunButton() {
  const [running, setRunning] = useState(false);
  const [msg,     setMsg]     = useState<string | null>(null);

  async function run() {
    setRunning(true);
    setMsg(null);
    try {
      const res = await fetch(`${API_BASE}/alpha/run`, { method: "POST" });
      const data = await res.json();
      setMsg(data.success
        ? `✓ ${data.patterns_found} padrões encontrados`
        : `Erro: ${data.error ?? "desconhecido"}`
      );
    } catch {
      setMsg("Falha na requisição");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex items-center gap-3">
      {msg && <span className="text-xs text-[#9ca3af]">{msg}</span>}
      <button
        onClick={run}
        disabled={running}
        className="px-4 py-1.5 text-xs font-semibold rounded-md bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:bg-blue-500/30 transition-colors disabled:opacity-50"
      >
        {running ? "Calculando…" : "Rodar Análise Alpha"}
      </button>
    </div>
  );
}

export default function AlphaPage() {
  return (
    <div className="min-h-screen bg-[#0a0e1a]">

      {/* Navbar */}
      <nav className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-screen-xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <polyline points="22 7 13.5 15.5 8.5 10.5 2 17" />
                <polyline points="16 7 22 7 22 13" />
              </svg>
            </div>
            <div>
              <span className="text-lg font-bold text-[#f9fafb]">TradeAI</span>
              <span className="ml-2 text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-mono">
                v9.0.0
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs text-[#6b7280] hover:text-[#f9fafb] transition-colors"
            >
              ← Dashboard
            </Link>
            <Link
              href="/analytics"
              className="text-xs text-[#6b7280] hover:text-[#f9fafb] transition-colors"
            >
              Analytics
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-screen-xl mx-auto px-6 py-8 flex flex-col gap-6">

        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-[#f9fafb]">Alpha Discovery</h1>
            <p className="text-sm text-[#9ca3af] mt-1">
              Fase 9 — Descoberta automática de vantagem estatística no histórico de sinais.
              Determinístico · Auditável · Sem IA.
            </p>
          </div>
          <RunButton />
        </header>

        {/* Row 1: Best Setups + Worst Setups */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <BestSetups />
          <WorstSetups />
        </div>

        {/* Row 2: Meta-Analytics + Setup Quality */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <MetaAnalytics />
          <SetupQualityPanel />
        </div>

        {/* Row 3: Heatmap (full width) */}
        <AlphaHeatmap />

        {/* Footer */}
        <footer className="text-center pt-4 border-t border-[#1f2937]">
          <p className="text-xs text-[#4b5563]">
            TradeAI v9.0.0 — Fase 9: Alpha Discovery Engine · Setup Quality Score · Meta-Analytics.{" "}
            <Link href="/" className="text-blue-400 hover:text-blue-300 underline transition-colors">
              Voltar ao Dashboard →
            </Link>
          </p>
        </footer>

      </main>
    </div>
  );
}
