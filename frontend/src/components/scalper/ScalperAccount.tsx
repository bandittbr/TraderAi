"use client";
import { useEffect, useState } from "react";

interface Account {
  balance:         number;
  initial_balance: number;
  peak_balance:    number;
  total_pnl:       number;
}

function safe(v: unknown, d = 0): number {
  const n = Number(v);
  return isFinite(n) ? n : d;
}

function pct(a: number, b: number) {
  if (!b) return "0.00";
  return ((a - b) / b * 100).toFixed(2);
}

export default function ScalperAccount() {
  const [acc, setAcc] = useState<Account | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/v1/scalper/account");
        if (r.ok) setAcc(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const bal  = safe(acc?.balance, 10_000);
  const init = safe(acc?.initial_balance, 10_000);
  const peak = safe(acc?.peak_balance, 10_000);
  const pnl  = safe(acc?.total_pnl);
  const pnlPositive = pnl >= 0;
  const dd   = peak > 0 ? ((peak - bal) / peak * 100) : 0;

  const MetricCard = ({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) => (
    <div className="rounded-xl p-4 flex flex-col gap-1" style={{ background: "#0d1525", border: "1px solid #141c2e" }}>
      <div className="text-[10px] text-[#3d5a80] uppercase tracking-widest">{label}</div>
      <div className={`text-xl font-bold font-mono ${color || "text-white"}`}>{value}</div>
      {sub && <div className="text-[10px] text-[#3d5a80]">{sub}</div>}
    </div>
  );

  return (
    <div className="rounded-2xl p-5" style={{ background: "#0a1020", border: "1px solid #141c2e" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Conta Scalper</h2>
        <span className="text-[10px] px-2 py-0.5 rounded-full font-mono"
          style={{ background: "#0d1525", color: "#3b82f6", border: "1px solid #1e3a5f" }}>
          Paper Trading
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard label="Saldo Atual" value={`$${bal.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
          sub={`${pct(bal, init)}% vs inicial`} />
        <MetricCard label="PnL Total"
          value={`${pnlPositive ? "+" : ""}$${pnl.toFixed(2)}`}
          color={pnlPositive ? "text-emerald-400" : "text-red-400"}
          sub={`${pnlPositive ? "+" : ""}${pct(bal, init)}%`} />
        <MetricCard label="Peak Balance" value={`$${peak.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`}
          sub="máximo histórico" />
        <MetricCard label="Drawdown" value={`${dd.toFixed(2)}%`}
          color={dd > 5 ? "text-red-400" : dd > 2 ? "text-amber-400" : "text-emerald-400"}
          sub="do pico" />
      </div>
    </div>
  );
}
