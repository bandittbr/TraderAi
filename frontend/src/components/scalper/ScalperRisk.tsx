"use client";
import { useEffect, useState } from "react";

interface RiskDay {
  date:               string;
  daily_pnl_usd:      number;
  daily_pnl_pct:      number;
  consecutive_losses: number;
  total_trades:       number;
  winning_trades:     number;
  losing_trades:      number;
  is_blocked:         boolean;
  block_reason:       string | null;
}

function safe(v: unknown, d = 0): number { const n = Number(v); return isFinite(n) ? n : d; }

export default function ScalperRisk() {
  const [risk,    setRisk]    = useState<RiskDay | null>(null);
  const [history, setHistory] = useState<RiskDay[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const [r1, r2] = await Promise.all([
          fetch("/api/v1/scalper/risk"),
          fetch("/api/v1/scalper/risk/history?days=7"),
        ]);
        if (r1.ok) setRisk(await r1.json());
        if (r2.ok) setHistory(await r2.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, []);

  const consec   = safe(risk?.consecutive_losses);
  const dailyPct = safe(risk?.daily_pnl_pct);

  return (
    <div className="rounded-2xl p-5" style={{ background: "#0a1020", border: "1px solid #141c2e" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Risk Stats</h2>
        <span className="text-[10px] px-2 py-0.5 rounded-full"
          style={{ background: "#052e16", color: "#22c55e", border: "1px solid #14532d" }}>
          LIVRE
        </span>
      </div>

      <div className="space-y-4">
        {/* Perdas consecutivas */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-[11px] text-[#4a6080]">Perdas Consecutivas</span>
            <span className={`text-xs font-mono font-bold ${consec >= 5 ? "text-red-400" : consec >= 3 ? "text-amber-400" : "text-emerald-400"}`}>
              {consec}
            </span>
          </div>
        </div>

        {/* PnL Diário */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <span className="text-[11px] text-[#4a6080]">PnL Diário</span>
            <span className={`text-xs font-mono font-bold ${dailyPct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
              {dailyPct >= 0 ? "+" : ""}{dailyPct.toFixed(2)}%
            </span>
          </div>
        </div>

        {/* Stats do dia */}
        <div className="grid grid-cols-3 gap-2 pt-2" style={{ borderTop: "1px solid #141c2e" }}>
          {[
            { label: "Trades Hoje", value: safe(risk?.total_trades).toString() },
            { label: "Wins",        value: safe(risk?.winning_trades).toString(), color: "text-emerald-400" },
            { label: "Losses",      value: safe(risk?.losing_trades).toString(),  color: "text-red-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="text-center">
              <div className={`text-lg font-bold font-mono ${color || "text-white"}`}>{value}</div>
              <div className="text-[9px] text-[#3d5a80] uppercase tracking-widest">{label}</div>
            </div>
          ))}
        </div>

        {/* Histórico 7 dias */}
        {history.length > 0 && (
          <div style={{ borderTop: "1px solid #141c2e", paddingTop: "12px" }}>
            <div className="text-[9px] text-[#3d5a80] uppercase tracking-widest mb-2">Últimos 7 dias</div>
            <div className="space-y-1">
              {history.slice(0, 5).map(d => (
                <div key={d.date} className="flex items-center justify-between text-[11px]">
                  <span className="text-[#4a6080] font-mono">{d.date.slice(5)}</span>
                  <span className="text-[#4a6080]">{d.total_trades} trades</span>
                  <span className={safe(d.daily_pnl_pct) >= 0 ? "text-emerald-400" : "text-red-400"}>
                    {safe(d.daily_pnl_pct) >= 0 ? "+" : ""}{safe(d.daily_pnl_pct).toFixed(2)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
