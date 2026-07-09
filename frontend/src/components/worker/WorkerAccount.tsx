"use client";

interface Props {
  account: {
    balance: number;
    initial_balance: number;
    peak_balance: number;
    total_pnl: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
  };
}

export default function WorkerAccount({ account }: Props) {
  const pnlPct = account.initial_balance > 0
    ? ((account.total_pnl / account.initial_balance) * 100)
    : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <div className="rounded-xl p-4 bg-[#0a1020] border border-[#141c2e]">
        <div className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">Saldo</div>
        <div className="text-lg font-bold text-white">${account.balance.toFixed(2)}</div>
        <div className="text-[10px] text-[#3b4a6b] mt-0.5">
          Inicial: ${account.initial_balance.toFixed(2)}
        </div>
      </div>

      <div className="rounded-xl p-4 bg-[#0a1020] border border-[#141c2e]">
        <div className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">P&L Total</div>
        <div className={`text-lg font-bold ${pnlPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
          {pnlPct >= 0 ? "+" : ""}{pnlPct.toFixed(2)}%
        </div>
        <div className="text-[10px] text-[#3b4a6b] mt-0.5">
          ${account.total_pnl >= 0 ? "+" : ""}{account.total_pnl.toFixed(2)} USD
        </div>
      </div>

      <div className="rounded-xl p-4 bg-[#0a1020] border border-[#141c2e]">
        <div className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">Peak</div>
        <div className="text-lg font-bold text-amber-400">${account.peak_balance.toFixed(2)}</div>
        <div className="text-[10px] text-[#3b4a6b] mt-0.5">
          Trades: {account.total_trades}
        </div>
      </div>

      <div className="rounded-xl p-4 bg-[#0a1020] border border-[#141c2e]">
        <div className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">Win / Loss</div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-emerald-400 font-bold">{account.winning_trades}</span>
          <span className="text-[#3b4a6b]">/</span>
          <span className="text-red-400 font-bold">{account.losing_trades}</span>
        </div>
        <div className="text-[10px] text-[#3b4a6b] mt-0.5">
          {account.total_trades > 0
            ? `WR: ${((account.winning_trades / account.total_trades) * 100).toFixed(1)}%`
            : "Sem trades"}
        </div>
      </div>
    </div>
  );
}
