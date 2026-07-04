/**
 * TradeAI - Componente: Signal Engine (Fase 3)
 * Exibe sinal BUY/SELL/NEUTRAL, confiança 0–100 e justificativas técnicas.
 */

"use client";

import type { SignalData, SignalType } from "@/types";
import { clsx } from "clsx";

// ── Configurações visuais por sinal ───────────────────────────────────────────

const SIGNAL_CONFIG: Record<SignalType, {
  bg: string; border: string; text: string; badge: string; icon: string; bar: string;
}> = {
  BUY: {
    bg:     "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text:   "text-emerald-400",
    badge:  "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    icon:   "↑",
    bar:    "bg-emerald-500",
  },
  SELL: {
    bg:     "bg-red-500/10",
    border: "border-red-500/30",
    text:   "text-red-400",
    badge:  "bg-red-500/20 text-red-300 border-red-500/40",
    icon:   "↓",
    bar:    "bg-red-500",
  },
  NEUTRAL: {
    bg:     "bg-amber-500/10",
    border: "border-amber-500/30",
    text:   "text-amber-400",
    badge:  "bg-amber-500/20 text-amber-300 border-amber-500/40",
    icon:   "→",
    bar:    "bg-amber-500",
  },
};

// ── Componente ────────────────────────────────────────────────────────────────

interface SignalEngineProps {
  signal:  SignalData | null;
  loading: boolean;
  symbol:  string;
}

export function SignalEngine({ signal, loading, symbol }: SignalEngineProps) {
  const cfg = signal ? SIGNAL_CONFIG[signal.signal] : null;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 flex flex-col gap-4">

      {/* Cabeçalho */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Signal Engine</h3>
          <p className="text-xs text-[#6b7280] mt-0.5">
            {symbol.replace("USDT", "")}/USDT · Sem IA · Regras técnicas
          </p>
        </div>
        {loading && (
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {!signal && !loading && (
        <p className="text-xs text-[#6b7280] text-center py-6">
          Aguardando geração de sinal...
        </p>
      )}

      {signal && cfg && (
        <>
          {/* Badge do sinal */}
          <div className={clsx("rounded-xl border p-4 flex items-center gap-4", cfg.bg, cfg.border)}>
            <span className={clsx("text-4xl font-black", cfg.text)}>{cfg.icon}</span>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={clsx("text-2xl font-black tracking-wider", cfg.text)}>
                  {signal.signal}
                </span>
                <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-semibold", cfg.badge)}>
                  {signal.confidence}% confiança
                </span>
              </div>
              <p className="text-xs text-[#6b7280]">
                {signal.signal === "BUY"
                  ? "Condições técnicas favoráveis para compra"
                  : signal.signal === "SELL"
                  ? "Condições técnicas favoráveis para venda"
                  : "Mercado sem direção clara — aguardar confirmação"}
              </p>
            </div>
          </div>

          {/* Barra de confiança */}
          <div>
            <div className="flex justify-between text-xs text-[#6b7280] mb-1.5">
              <span>Confiança</span>
              <span>{signal.confidence}%</span>
            </div>
            <div className="h-2 rounded-full bg-[#1f2937] overflow-hidden">
              <div
                className={clsx("h-full rounded-full transition-all duration-700", cfg.bar)}
                style={{ width: `${signal.confidence}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-[#4b5563] mt-0.5">
              <span>0</span><span>50</span><span>100</span>
            </div>
          </div>

          {/* Critérios atendidos */}
          {signal.reasons.length > 0 && (
            <div>
              <p className="text-xs text-[#6b7280] mb-2 font-semibold uppercase tracking-wider">
                Critérios atendidos
              </p>
              <div className="flex flex-col gap-1.5">
                {signal.reasons.map((reason, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <div className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", cfg.bar)} />
                    <span className="text-xs text-[#9ca3af]">{reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Footer */}
      <div className="pt-1 border-t border-[#1f2937]">
        <p className="text-xs text-[#4b5563]">
          Fase 4+: integrar IA, funding rate e sentimento como critérios extras
        </p>
      </div>
    </div>
  );
}
