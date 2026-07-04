"use client";
import { useEffect, useState } from "react";

interface Signal {
  id:            number;
  symbol:        string;
  direction:     string;
  trend_15m:     string;
  confirm_5m:    boolean;
  entry_1m:      boolean;
  confidence:    number;
  price:         number;
  rsi_1m:        number | null;
  rsi_5m:        number | null;
  acted_on:      boolean;
  reject_reason: string | null;
  emitted_at:    string;
}

function safe(v: unknown, d = 0): number { const n = Number(v); return isFinite(n) ? n : d; }
function ago(dt: string) {
  const secs = Math.floor((Date.now() - new Date(dt).getTime()) / 1000);
  if (secs < 60)  return `${secs}s`;
  if (secs < 3600) return `${Math.floor(secs/60)}m`;
  return `${Math.floor(secs/3600)}h`;
}

export default function ScalperSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [sym, setSym]         = useState("ALL");

  const SYMBOLS = ["ALL", "BTC", "ETH", "SOL", "AVAX"];

  useEffect(() => {
    const load = async () => {
      const q = sym === "ALL" ? "" : `&symbol=${sym}USDT`;
      try {
        const r = await fetch(`/api/v1/scalper/signals?limit=50${q}`);
        if (r.ok) setSignals(await r.json());
      } catch {}
    };
    load();
    const id = setInterval(load, 10_000);
    return () => clearInterval(id);
  }, [sym]);

  const dirColor: Record<string, string> = {
    LONG:  "text-emerald-400",
    SHORT: "text-red-400",
    NONE:  "text-[#2d4060]",
  };

  const trendColor: Record<string, string> = {
    BULL:     "text-emerald-400",
    BEAR:     "text-red-400",
    SIDEWAYS: "text-amber-400",
  };

  return (
    <div className="rounded-2xl p-5" style={{ background: "#0a1020", border: "1px solid #141c2e" }}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-white">Sinais MTF</h2>
        <div className="flex gap-1">
          {SYMBOLS.map(s => (
            <button key={s} onClick={() => setSym(s)}
              className="text-[10px] px-2 py-0.5 rounded transition-all"
              style={{
                background: sym === s ? "#1e3a5f" : "#0d1525",
                color:      sym === s ? "#60a5fa" : "#3d5a80",
                border:     "1px solid " + (sym === s ? "#2563eb" : "#141c2e"),
              }}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {signals.length === 0 ? (
        <div className="text-center py-8 text-[#2d4060] text-sm">Aguardando sinais...</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-[#2d4060] uppercase tracking-widest text-[9px]">
                <th className="text-left pb-2">Tempo</th>
                <th className="text-left pb-2">Ativo</th>
                <th className="text-center pb-2">Direção</th>
                <th className="text-center pb-2">Trend 15m</th>
                <th className="text-center pb-2">5m Conf</th>
                <th className="text-center pb-2">1m Entry</th>
                <th className="text-right pb-2">Conf</th>
                <th className="text-right pb-2">RSI 1m</th>
                <th className="text-center pb-2">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: "#0d1525" }}>
              {signals.map(s => (
                <tr key={s.id}>
                  <td className="py-1.5 text-[#2d4060] font-mono text-[10px]">{ago(s.emitted_at)}</td>
                  <td className="py-1.5 font-mono text-white">{s.symbol.replace("USDT","")}</td>
                  <td className={`py-1.5 text-center font-bold ${dirColor[s.direction] || "text-[#4a6080]"}`}>
                    {s.direction}
                  </td>
                  <td className={`py-1.5 text-center ${trendColor[s.trend_15m] || "text-[#4a6080]"}`}>
                    {s.trend_15m}
                  </td>
                  <td className="py-1.5 text-center">
                    <span className={s.confirm_5m ? "text-emerald-400" : "text-[#2d4060]"}>
                      {s.confirm_5m ? "✓" : "×"}
                    </span>
                  </td>
                  <td className="py-1.5 text-center">
                    <span className={s.entry_1m ? "text-emerald-400" : "text-[#2d4060]"}>
                      {s.entry_1m ? "✓" : "×"}
                    </span>
                  </td>
                  <td className="py-1.5 text-right font-mono text-[#8aa4c8]">
                    {safe(s.confidence).toFixed(0)}%
                  </td>
                  <td className="py-1.5 text-right font-mono text-[#4a6080]">
                    {s.rsi_1m ? safe(s.rsi_1m).toFixed(1) : "—"}
                  </td>
                  <td className="py-1.5 text-center">
                    {s.acted_on
                      ? <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: "#052e16", color: "#22c55e" }}>TRADE</span>
                      : <span className="text-[#2d4060] text-[10px]">skip</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
