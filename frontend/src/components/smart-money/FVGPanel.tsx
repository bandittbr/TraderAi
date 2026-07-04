"use client";

import { useEffect, useState, useCallback } from "react";
import { clsx } from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SYMBOLS    = ["BTCUSDT","ETHUSDT","SOLUSDT"];
const TIMEFRAMES = ["15m","1h","4h"];

interface FVGItem {
  fvg_type?: string | null;
  status?: string | null;
  gap_top: number;
  gap_bottom: number;
  gap_size_pct?: number | null;
  distance_pct?: number | null;
  relevance?: number | null;
  is_filled?: boolean | null;
}
interface FVGsData {
  symbol: string; timeframe: string;
  active_bullish: FVGItem[]; active_bearish: FVGItem[];
  has_bullish_fvg: boolean; has_bearish_fvg: boolean;
  computed_at: string | null;
}

function fmt(n: number, dec = 2) { return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }); }

function RelevanceBar({ value }: { value: number }) {
  const color = value >= 70 ? "bg-emerald-500" : value >= 40 ? "bg-yellow-500" : "bg-gray-600";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1 w-12 bg-[#1f2937] rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value ?? 0}%` }} />
      </div>
      <span className="text-[10px] text-[#6b7280]">{(value ?? 0).toFixed(0)}</span>
    </div>
  );
}

export function FVGPanel() {
  const [symbol,    setSymbol]    = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [data,      setData]      = useState<FVGsData | null>(null);
  const [loading,   setLoading]   = useState(false);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/smc/${symbol}/fvgs?timeframe=${timeframe}`);
      if (r.ok) setData(await r.json());
    } catch { /* noop */ } finally { setLoading(false); }
  }, [symbol, timeframe]);

  useEffect(() => { fetch_(); const id = setInterval(fetch_, 60_000); return () => clearInterval(id); }, [fetch_]);

  function FVGRow({ item, dir }: { item: FVGItem; dir: "bull" | "bear" }) {
    const isBull = dir === "bull";
    return (
      <div className={clsx(
        "rounded-lg p-2.5 border text-xs",
        isBull ? "bg-emerald-500/5 border-emerald-500/15" : "bg-red-500/5 border-red-500/15"
      )}>
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <span className={`text-[10px] font-bold ${isBull ? "text-emerald-400" : "text-red-400"}`}>
              {isBull ? "▲ BULL" : "▼ BEAR"}
            </span>
            <span className={clsx(
              "text-[9px] px-1 rounded font-semibold",
              (item.status ?? "") === "ACTIVE"   ? "bg-blue-500/20 text-blue-400" :
              (item.status ?? "") === "PARTIAL"  ? "bg-yellow-500/20 text-yellow-400" :
              "bg-gray-500/20 text-gray-400"
            )}>{item.status ?? "—"}</span>
          </div>
          <RelevanceBar value={item.relevance ?? 0} />
        </div>
        <div className="flex gap-4 text-[10px] text-[#9ca3af]">
          <span>Top: <span className="font-mono text-[#f9fafb]">${fmt(item.gap_top)}</span></span>
          <span>Bot: <span className="font-mono text-[#f9fafb]">${fmt(item.gap_bottom)}</span></span>
          <span className="ml-auto">{(item.gap_size_pct ?? 0).toFixed(3)}%</span>
        </div>
        {(item.distance_pct ?? 0) > 0 && (
          <p className={`text-[10px] mt-1 ${isBull ? "text-emerald-400/70" : "text-red-400/70"}`}>
            {(item.distance_pct ?? 0).toFixed(2)}% do preço
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Fair Value Gaps</h3>
          <p className="text-[10px] text-[#4b5563] mt-0.5">Imbalances institucionais ativos</p>
        </div>
        <button onClick={fetch_} disabled={loading} className="text-xs text-[#6b7280] hover:text-white disabled:opacity-40">
          {loading ? "..." : "↻"}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1">
          {SYMBOLS.map(s => (
            <button key={s} onClick={() => setSymbol(s)} className={clsx(
              "px-2.5 py-1 text-xs rounded-md font-medium border transition-colors",
              symbol === s ? "bg-blue-500/20 text-blue-400 border-blue-500/30" : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-white"
            )}>{s.replace("USDT","")}</button>
          ))}
        </div>
        <div className="flex gap-1">
          {TIMEFRAMES.map(tf => (
            <button key={tf} onClick={() => setTimeframe(tf)} className={clsx(
              "px-2.5 py-1 text-xs rounded-md font-medium border transition-colors",
              timeframe === tf ? "bg-purple-500/20 text-purple-400 border-purple-500/30" : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-white"
            )}>{tf}</button>
          ))}
        </div>
      </div>

      {loading && !data && (
        <div className="h-24 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {data && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className="text-[10px] text-[#6b7280] mb-2 uppercase tracking-wide">
              Bullish FVGs ({data.active_bullish.length})
              {data.has_bullish_fvg && <span className="ml-1 text-emerald-400">● Próximo</span>}
            </p>
            <div className="space-y-2">
              {data.active_bullish.length === 0 ? (
                <p className="text-[10px] text-[#4b5563]">Nenhum ativo</p>
              ) : data.active_bullish.map((f, i) => <FVGRow key={i} item={f} dir="bull" />)}
            </div>
          </div>
          <div>
            <p className="text-[10px] text-[#6b7280] mb-2 uppercase tracking-wide">
              Bearish FVGs ({data.active_bearish.length})
              {data.has_bearish_fvg && <span className="ml-1 text-red-400">● Próximo</span>}
            </p>
            <div className="space-y-2">
              {data.active_bearish.length === 0 ? (
                <p className="text-[10px] text-[#4b5563]">Nenhum ativo</p>
              ) : data.active_bearish.map((f, i) => <FVGRow key={i} item={f} dir="bear" />)}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
