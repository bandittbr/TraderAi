"use client";

import { useEffect, useState, useCallback } from "react";
import { clsx } from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SYMBOLS  = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];

interface SweepEvent {
  type?: string | null;
  strength?: string | null;
  price: number;
  swept_level: number;
  timestamp: number;
  penetration_pct?: number | null;
  is_stop_hunt?: boolean | null;
}
interface SweepsData {
  symbol: string; timeframe: string;
  events: SweepEvent[];
  buy_count: number; sell_count: number;
  sweep_bias?: string | null;
  computed_at: string | null;
}

function fmt(n: number | null | undefined, dec = 2) {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function safeStr(v: string | null | undefined): string {
  return v ?? "";
}

function typeColor(t: string | null | undefined) {
  const v = safeStr(t).toUpperCase();
  if (v.includes("BUY"))  return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
  if (v.includes("SELL")) return "text-red-400 bg-red-500/10 border-red-500/20";
  if (v === "STOP_HUNT")  return "text-orange-400 bg-orange-500/10 border-orange-500/20";
  if (!v)                 return "text-gray-400 bg-gray-500/10 border-gray-500/20";
  return "text-yellow-400 bg-yellow-500/10 border-yellow-500/20";
}

function typeLabel(t: string | null | undefined): string {
  const v = safeStr(t);
  return v ? v.replace(/_/g, " ") : "—";
}

export function SweepMonitor() {
  const [symbol,   setSymbol]   = useState("BTCUSDT");
  const [data,     setData]     = useState<Record<string, SweepsData>>({});
  const [loading,  setLoading]  = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.all(
        SYMBOLS.map(s => fetch(`${API_BASE}/smc/${s}/sweeps?timeframe=1h`).then(r => r.ok ? r.json() : null))
      );
      const map: Record<string, SweepsData> = {};
      SYMBOLS.forEach((s, i) => { if (results[i]) map[s] = results[i]; });
      setData(map);
    } catch { /* noop */ } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAll(); const id = setInterval(fetchAll, 60_000); return () => clearInterval(id); }, [fetchAll]);

  const d = data[symbol];

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Sweep Monitor</h3>
          <p className="text-[10px] text-[#4b5563] mt-0.5">Liquidity Sweeps · Stop Hunts · False Breaks</p>
        </div>
        <button onClick={fetchAll} disabled={loading} className="text-xs text-[#6b7280] hover:text-white disabled:opacity-40">
          {loading ? "..." : "↻"}
        </button>
      </div>

      {/* Symbol tabs */}
      <div className="flex gap-1">
        {SYMBOLS.map(s => {
          const d = data[s];
          const hasBuy  = (d?.buy_count  ?? 0) > 0;
          const hasSell = (d?.sell_count ?? 0) > 0;
          return (
            <button key={s} onClick={() => setSymbol(s)} className={clsx(
              "flex-1 px-2 py-1.5 rounded-md text-xs font-medium border transition-colors relative",
              symbol === s ? "bg-blue-500/20 text-blue-400 border-blue-500/30" : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-white"
            )}>
              {s.replace("USDT","")}
              {(hasBuy || hasSell) && (
                <span className={clsx(
                  "absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full",
                  hasBuy && hasSell ? "bg-yellow-400" : hasBuy ? "bg-emerald-400" : "bg-red-400"
                )} />
              )}
            </button>
          );
        })}
      </div>

      {loading && !d && (
        <div className="h-32 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {d && (
        <div className="space-y-2">
          {/* Summary */}
          <div className="flex items-center gap-3 text-xs">
            <span className="text-emerald-400 font-semibold">{d.buy_count ?? 0} Buy</span>
            <span className="text-red-400 font-semibold">{d.sell_count ?? 0} Sell</span>
            <span className={clsx("font-bold ml-auto", {
              "text-emerald-400": d.sweep_bias === "BULLISH",
              "text-red-400":     d.sweep_bias === "BEARISH",
              "text-[#6b7280]":   !d.sweep_bias || d.sweep_bias === "NEUTRAL",
            })}>Bias: {d.sweep_bias ?? "NEUTRAL"}</span>
          </div>

          {(d.events?.length ?? 0) === 0 ? (
            <div className="text-center py-6 text-[#4b5563] text-xs">
              Nenhum sweep detectado nos últimos 5 candles
            </div>
          ) : (
            <div className="space-y-1.5 max-h-52 overflow-y-auto">
              {[...(d.events ?? [])].reverse().map((e, i) => (
                <div key={i} className={clsx("rounded-lg p-2.5 border text-xs", typeColor(e.type))}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold">{typeLabel(e.type)}</span>
                      {e.is_stop_hunt && (
                        <span className="text-[9px] bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded font-bold">STOP HUNT</span>
                      )}
                      <span className="text-[10px] opacity-70">{safeStr(e.strength)}</span>
                    </div>
                    <span className="text-[10px] opacity-60 font-mono">
                      {new Date((e.timestamp ?? 0) * 1000).toLocaleTimeString("pt-BR")}
                    </span>
                  </div>
                  <div className="flex gap-4 text-[10px] opacity-80">
                    <span>Wick: <span className="font-mono font-bold">${fmt(e.price)}</span></span>
                    <span>Nível: <span className="font-mono">${fmt(e.swept_level)}</span></span>
                    <span>+{(e.penetration_pct ?? 0).toFixed(3)}%</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
