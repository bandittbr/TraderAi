"use client";
import { useEffect, useState } from "react";

interface Trade {
  id:                   number;
  symbol:               string;
  trade_side:           string;
  trend_15m:            string;
  confidence:           number;
  entry_price:          number;
  exit_price:           number | null;
  stop_loss_price:      number;
  take_profit_price:    number;
  break_even_activated: boolean;
  trailing_stop_active: boolean;
  trailing_stop_price:  number | null;
  pnl:                  number | null;
  pnl_pct:              number | null;
  status:               string;
  close_reason:         string | null;
  opened_at:            string;
  closed_at:            string | null;
  duration_minutes:     number | null;
}

function safe(v: unknown, d = 0): number { const n = Number(v); return isFinite(n) ? n : d; }
function fmt(dt: string | null) {
  if (!dt) return "—";
  return new Date(dt).toLocaleString("pt-BR", { day:"2-digit", month:"2-digit", hour:"2-digit", minute:"2-digit" });
}

export default function ScalperTrades() {
  const [trades,  setTrades]  = useState<Trade[]>([]);
  const [tab,     setTab]     = useState<"open"|"closed">("open");

  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch(`/api/v1/scalper/trades?status=${tab}&limit=50`);
        if (r.ok) setTrades(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, [tab]);

  const reasonColor: Record<string, string> = {
    TAKE_PROFIT:    "text-emerald-400",
    TRAILING_STOP:  "text-blue-400",
    STOP_LOSS:      "text-red-400",
    BREAK_EVEN_STOP:"text-amber-400",
    SIGNAL_CLOSE:   "text-purple-400",
    TIME_STOP:      "text-[#4a6080]",
  };

  return (
    <div className="rounded-2xl p-5" style={{ background: "#0a1020", border: "1px solid #141c2e" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Trades</h2>
        <div className="flex gap-1">
          {(["open","closed"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className="text-[11px] px-3 py-1 rounded-lg capitalize transition-all"
              style={{
                background: tab === t ? "#1e3a5f" : "#0d1525",
                color:      tab === t ? "#60a5fa"  : "#3d5a80",
                border:     "1px solid " + (tab === t ? "#2563eb" : "#141c2e"),
              }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      {trades.length === 0 ? (
        <div className="text-center py-8 text-[#2d4060] text-sm">
          {tab === "open" ? "Nenhum trade aberto" : "Nenhum trade fechado"}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-[#2d4060] uppercase tracking-widest text-[9px]">
                <th className="text-left pb-2">Ativo</th>
                <th className="text-left pb-2">Lado</th>
                <th className="text-right pb-2">Entrada</th>
                {tab === "open" && <th className="text-right pb-2">SL / TP</th>}
                {tab === "closed" && <th className="text-right pb-2">Saída</th>}
                <th className="text-right pb-2">PnL</th>
                {tab === "open" && <th className="text-center pb-2">BE/TS</th>}
                {tab === "closed" && <th className="text-center pb-2">Motivo</th>}
                <th className="text-right pb-2">Conf</th>
                <th className="text-right pb-2">Abertura</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "#0d1525" }}>
              {trades.map(t => {
                const pnl = safe(t.pnl);
                const pct = safe(t.pnl_pct);
                const isLong = t.trade_side === "LONG";
                return (
                  <tr key={t.id}>
                    <td className="py-2 font-mono text-white">{t.symbol.replace("USDT","")}</td>
                    <td className="py-2">
                      <span className={`font-bold ${isLong ? "text-emerald-400" : "text-red-400"}`}>
                        {t.trade_side}
                      </span>
                    </td>
                    <td className="py-2 text-right font-mono text-[#8aa4c8]">
                      ${safe(t.entry_price).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                    </td>
                    {tab === "open" && (
                      <td className="py-2 text-right font-mono text-[10px]">
                        <span className="text-red-400">${safe(t.stop_loss_price).toFixed(2)}</span>
                        <span className="text-[#2d4060]"> / </span>
                        <span className="text-emerald-400">${safe(t.take_profit_price).toFixed(2)}</span>
                      </td>
                    )}
                    {tab === "closed" && (
                      <td className="py-2 text-right font-mono text-[#8aa4c8]">
                        ${t.exit_price ? safe(t.exit_price).toFixed(2) : "—"}
                      </td>
                    )}
                    <td className="py-2 text-right font-mono">
                      {t.status === "CLOSED" ? (
                        <span className={pnl >= 0 ? "text-emerald-400" : "text-red-400"}>
                          {pnl >= 0 ? "+" : ""}{pct.toFixed(2)}%
                        </span>
                      ) : <span className="text-[#2d4060]">—</span>}
                    </td>
                    {tab === "open" && (
                      <td className="py-2 text-center text-[10px]">
                        {t.break_even_activated && <span className="text-amber-400 mr-1">BE</span>}
                        {t.trailing_stop_active  && <span className="text-blue-400">TS</span>}
                        {!t.break_even_activated && !t.trailing_stop_active && <span className="text-[#2d4060]">—</span>}
                      </td>
                    )}
                    {tab === "closed" && (
                      <td className={`py-2 text-center ${reasonColor[t.close_reason || ""] || "text-[#4a6080]"}`}>
                        {(t.close_reason || "—").replace("_"," ")}
                      </td>
                    )}
                    <td className="py-2 text-right text-[#4a6080]">{safe(t.confidence).toFixed(0)}%</td>
                    <td className="py-2 text-right text-[#2d4060] font-mono text-[10px]">{fmt(t.opened_at)}</td>
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
