"use client";

import type { PaperTradeResponse } from "@/types";

interface Props {
  trades:  PaperTradeResponse[];
  loading?: boolean;
}

function fmt(n: number | null, decimals = 2) {
  if (n === null || n === undefined) return "—";
  return n.toFixed(decimals);
}

function fmtDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function TradesTable({ trades, loading }: Props) {
  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <h3 className="text-sm font-semibold text-[#f9fafb] mb-4">Operações</h3>

      {loading ? (
        <div className="h-32 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : trades.length === 0 ? (
        <div className="h-32 flex flex-col items-center justify-center gap-2">
          <p className="text-sm text-[#6b7280]">Nenhuma operação registrada</p>
          <p className="text-xs text-[#4b5563]">Os trades aparecem quando o sinal BUY ≥ 70% for detectado</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-[#6b7280] border-b border-[#1f2937]">
                <th className="text-left py-2 pr-4">Data</th>
                <th className="text-left py-2 pr-4">Ativo</th>
                <th className="text-center py-2 pr-4">Side</th>
                <th className="text-right py-2 pr-4">Entrada</th>
                <th className="text-right py-2 pr-4">Saída</th>
                <th className="text-right py-2 pr-4">PnL</th>
                <th className="text-right py-2 pr-4">PnL %</th>
                <th className="text-right py-2 pr-4">Conf.</th>
                <th className="text-center py-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => {
                const pnlPos = (t.pnl ?? 0) >= 0;
                const side   = t.trade_side ?? "LONG";
                return (
                  <tr
                    key={t.id}
                    className="border-b border-[#1f2937]/50 hover:bg-[#1f2937]/30 transition-colors"
                  >
                    <td className="py-2 pr-4 text-[#6b7280]">{fmtDate(t.opened_at)}</td>
                    <td className="py-2 pr-4 font-medium text-[#f9fafb]">
                      {t.symbol.replace("USDT", "")}
                    </td>
                    <td className="py-2 pr-4 text-center">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        side === "LONG"
                          ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                          : "bg-red-500/15 text-red-400 border-red-500/30"
                      }`}>
                        {side}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-right text-[#9ca3af]">
                      ${fmt(t.entry_price)}
                    </td>
                    <td className="py-2 pr-4 text-right text-[#9ca3af]">
                      {t.exit_price ? `$${fmt(t.exit_price)}` : "—"}
                    </td>
                    <td className={`py-2 pr-4 text-right font-semibold ${
                      t.pnl === null ? "text-[#6b7280]"
                      : pnlPos ? "text-[#10b981]" : "text-[#ef4444]"
                    }`}>
                      {t.pnl === null ? "—" : `${pnlPos ? "+" : ""}$${fmt(t.pnl)}`}
                    </td>
                    <td className={`py-2 pr-4 text-right ${
                      t.pnl_percent === null ? "text-[#6b7280]"
                      : pnlPos ? "text-[#10b981]" : "text-[#ef4444]"
                    }`}>
                      {t.pnl_percent === null
                        ? "—"
                        : `${t.pnl_percent >= 0 ? "+" : ""}${fmt(t.pnl_percent)}%`}
                    </td>
                    <td className="py-2 pr-4 text-right text-[#9ca3af]">
                      {t.confidence.toFixed(0)}%
                    </td>
                    <td className="py-2 text-center">
                      {t.status === "OPEN" ? (
                        <span className="px-2 py-0.5 rounded-full text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30">
                          ABERTO
                        </span>
                      ) : (
                        <span className={`px-2 py-0.5 rounded-full text-[10px] border ${
                          pnlPos
                            ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                            : "bg-red-500/20 text-red-400 border-red-500/30"
                        }`}>
                          {pnlPos ? "WIN" : "LOSS"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
