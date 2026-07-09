/**
 * TradeAI - Componente: Histórico de Sinais (Fase 6 — Analytics)
 * Lista os últimos sinais emitidos pelo Signal Engine, com resultado real
 * (WIN/LOSS/OPEN/MISSED) via GET /api/v1/analytics/signals.
 */

"use client";

import type { SignalHistoryItem, SignalType, SignalOutcome } from "@/types";
import { clsx } from "clsx";

interface Props {
  data:    SignalHistoryItem[];
  loading: boolean;
}

const SIGNAL_STYLE: Record<SignalType, string> = {
  BUY:     "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  SELL:    "text-red-400 bg-red-500/10 border-red-500/20",
  NEUTRAL: "text-amber-400 bg-amber-500/10 border-amber-500/20",
};

const OUTCOME_STYLE: Record<SignalOutcome, string> = {
  WIN:    "text-emerald-400",
  LOSS:   "text-red-400",
  OPEN:   "text-blue-400",
  MISSED: "text-[#6b7280]",
};

const OUTCOME_LABEL: Record<SignalOutcome, string> = {
  WIN:    "Ganho",
  LOSS:   "Perda",
  OPEN:   "Aberto",
  MISSED: "Sem posição",
};

function fmtDate(iso: string) {
  const d = new Date(iso);
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 3600)  return `${Math.floor(diff / 60)}m atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

export function SignalHistoryPanel({ data, loading }: Props) {
  const wins  = data.filter((s) => s.outcome === "WIN").length;
  const resolved = data.filter((s) => s.outcome === "WIN" || s.outcome === "LOSS").length;
  const winRate = resolved > 0 ? Math.round((wins / resolved) * 100) : null;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Histórico de Sinais</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">Últimos sinais emitidos pelo Signal Engine</p>
        </div>
        {winRate !== null && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-[#1f2937] text-[#9ca3af]">
            Win rate: <span className="text-[#f9fafb] font-semibold">{winRate}%</span>
          </span>
        )}
      </div>

      {loading ? (
        <div className="h-40 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : data.length === 0 ? (
        <div className="h-40 flex flex-col items-center justify-center gap-2">
          <p className="text-sm text-[#6b7280]">Nenhum sinal registrado no período</p>
          <p className="text-xs text-[#4b5563]">Sinais aparecem aqui assim que o Signal Engine emitir</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          {data.map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between gap-3 p-3 rounded-lg bg-[#0a0e1a] border border-[#1f2937]"
            >
              <div className="flex items-center gap-3 min-w-0">
                <span className={clsx(
                  "shrink-0 text-[10px] font-bold px-2 py-0.5 rounded border",
                  SIGNAL_STYLE[s.signal],
                )}>
                  {s.signal}
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-[#f9fafb] truncate">
                    {s.symbol.replace("USDT", "")}/USDT
                    <span className="text-[#6b7280] font-normal ml-1.5">{s.confidence.toFixed(0)}% conf.</span>
                  </p>
                  <p className="text-[10px] text-[#4b5563] mt-0.5">
                    {fmtDate(s.emitted_at)} · {s.regime}
                  </p>
                </div>
              </div>

              <div className="text-right shrink-0">
                <p className={clsx("text-xs font-semibold", OUTCOME_STYLE[s.outcome])}>
                  {OUTCOME_LABEL[s.outcome]}
                </p>
                {s.pnl_pct !== null && (
                  <p className={clsx("text-[10px] mt-0.5", s.pnl_pct >= 0 ? "text-emerald-400" : "text-red-400")}>
                    {s.pnl_pct >= 0 ? "+" : ""}{s.pnl_pct.toFixed(2)}%
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
