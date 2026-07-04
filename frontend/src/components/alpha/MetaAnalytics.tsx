/**
 * Fase 9 — Alpha: Meta-Analytics (melhores ativo, regime, contexto, SMC, técnico)
 */
"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";

interface DimensionStats {
  dimension:      string;
  dimension_type: string;
  resolved:       number;
  win_rate:       number;
  profit_factor:  number;
  score:          number;
}

interface MetaReport {
  by_symbol:      DimensionStats[];
  by_timeframe:   DimensionStats[];
  by_regime:      DimensionStats[];
  by_context:     DimensionStats[];
  by_smc_combo:   DimensionStats[];
  by_technical:   DimensionStats[];
  best_symbol:    string | null;
  best_timeframe: string | null;
  best_regime:    string | null;
  best_context:   string | null;
  best_smc_combo: string | null;
  best_technical: string | null;
  total_resolved: number;
  baseline_wr:    number;
  baseline_pf:    number;
}

const TABS = [
  { key: "by_symbol",    label: "Ativos" },
  { key: "by_regime",    label: "Regime" },
  { key: "by_technical", label: "Técnico" },
  { key: "by_smc_combo", label: "SMC" },
  { key: "by_context",   label: "Contexto" },
] as const;

type TabKey = typeof TABS[number]["key"];

function DimRow({ d, baseline }: { d: DimensionStats; baseline: number }) {
  const diff = d.win_rate - baseline;
  return (
    <div className="flex items-center gap-3 py-2 border-b border-[#1f2937] last:border-0">
      <span className="text-xs font-mono text-[#e5e7eb] w-28 truncate">{d.dimension}</span>
      <div className="flex-1">
        <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(d.win_rate, 100)}%`,
              background: d.win_rate > baseline ? "#10b981" : "#ef4444",
            }}
          />
        </div>
      </div>
      <span className="text-xs font-semibold w-14 text-right"
        style={{ color: d.win_rate > baseline ? "#10b981" : "#ef4444" }}
      >
        {d.win_rate.toFixed(1)}%
      </span>
      <span className="text-xs text-[#6b7280] w-12 text-right">PF {d.profit_factor.toFixed(2)}</span>
      <span className={`text-[10px] w-10 text-right font-mono ${diff > 0 ? "text-emerald-400" : "text-red-400"}`}>
        {diff > 0 ? "+" : ""}{diff.toFixed(1)}%
      </span>
    </div>
  );
}

export function MetaAnalytics() {
  const [report,  setReport]  = useState<MetaReport | null>(null);
  const [tab,     setTab]     = useState<TabKey>("by_symbol");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/alpha/report`);
        if (res.ok) setReport(await res.json());
      } catch {}
      finally { setLoading(false); }
    }
    load();
    const id = setInterval(load, 300_000);
    return () => clearInterval(id);
  }, []);

  const rows: DimensionStats[] = report ? (report[tab] as DimensionStats[]) : [];
  const baseline = report?.baseline_wr ?? 50;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-purple-400 inline-block" />
          Meta-Analytics
        </h3>
        {report && (
          <span className="text-[10px] text-[#6b7280]">
            Baseline WR {report.baseline_wr.toFixed(1)}% | {report.total_resolved} sinais
          </span>
        )}
      </div>

      {/* Melhores em destaque */}
      {report && (
        <div className="grid grid-cols-3 gap-2 mb-4">
          {[
            { label: "Melhor Ativo",   value: report.best_symbol },
            { label: "Melhor Regime",  value: report.best_regime },
            { label: "Melhor SMC",     value: report.best_smc_combo },
          ].map(({ label, value }) => (
            <div key={label} className="bg-[#0f1623] rounded-lg p-2 text-center border border-[#1f2937]">
              <p className="text-[10px] text-[#6b7280]">{label}</p>
              <p className="text-xs font-bold text-emerald-400 truncate mt-0.5">
                {value ?? "—"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-3 flex-wrap">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`text-xs px-2.5 py-1 rounded-md transition-all ${
              tab === key
                ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                : "text-[#6b7280] hover:text-[#9ca3af]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-xs text-[#6b7280] text-center py-6">Calculando…</div>
      ) : rows.length === 0 ? (
        <div className="text-xs text-[#4b5563] text-center py-4">
          Dados insuficientes para esta dimensão.
        </div>
      ) : (
        <div className="max-h-[280px] overflow-y-auto pr-1">
          {rows.slice(0, 10).map((d) => (
            <DimRow key={d.dimension} d={d} baseline={baseline} />
          ))}
        </div>
      )}
    </div>
  );
}
