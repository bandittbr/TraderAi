"use client";

import type { PaperAccountResponse } from "@/types";

interface Props {
  account: PaperAccountResponse | null;
  loading?: boolean;
}

export function PaperAccountCard({ account, loading }: Props) {
  const pnlPositive = (account?.pnl_total ?? 0) >= 0;

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Conta Virtual</h3>
        <span className="text-xs text-[#4b5563] bg-[#1f2937] px-2 py-0.5 rounded-full">
          Paper Trading
        </span>
      </div>

      {loading || !account ? (
        <div className="h-20 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="space-y-3">
          {/* Saldo atual */}
          <div>
            <p className="text-xs text-[#6b7280] mb-0.5">Saldo Atual</p>
            <p className="text-2xl font-bold text-[#f9fafb]">
              ${account.balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>

          {/* PnL */}
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-[#6b7280]">Lucro/Prejuízo</p>
              <p className={`text-sm font-semibold ${pnlPositive ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {pnlPositive ? "+" : ""}${account.pnl_total.toFixed(2)}
              </p>
            </div>
            <div>
              <p className="text-xs text-[#6b7280]">Retorno</p>
              <p className={`text-sm font-semibold ${pnlPositive ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                {pnlPositive ? "+" : ""}{account.pnl_pct.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="text-xs text-[#6b7280]">Capital Inicial</p>
              <p className="text-sm font-semibold text-[#9ca3af]">
                ${account.initial_balance.toFixed(2)}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
