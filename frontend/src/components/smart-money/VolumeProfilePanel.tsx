"use client";

import { useEffect, useState, useCallback } from "react";
import { clsx } from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SYMBOLS    = ["BTCUSDT","ETHUSDT","SOLUSDT"];
const TIMEFRAMES = ["15m","1h","4h","1d"];

interface VPData {
  symbol: string; timeframe: string;
  volume_profile_score: number;
  poc: number | null; value_area_high: number | null; value_area_low: number | null;
  hvn_levels: number[]; lvn_levels: number[];
  near_hvn: boolean; near_lvn: boolean; price_in_value_area: boolean;
  computed_at: string | null;
}

function fmt(n: number | null | undefined, dec = 2) {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

export function VolumeProfilePanel() {
  const [symbol,    setSymbol]    = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [data,      setData]      = useState<VPData | null>(null);
  const [loading,   setLoading]   = useState(false);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/smc/${symbol}/volume?timeframe=${timeframe}`);
      if (r.ok) setData(await r.json());
    } catch { /* noop */ } finally { setLoading(false); }
  }, [symbol, timeframe]);

  useEffect(() => { fetch_(); const id = setInterval(fetch_, 60_000); return () => clearInterval(id); }, [fetch_]);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Volume Profile</h3>
          <p className="text-[10px] text-[#4b5563] mt-0.5">HVN · LVN · POC · Value Area</p>
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
        <div className="space-y-3">
          {/* Score */}
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <div className="flex justify-between text-[10px] mb-1">
                <span className="text-[#6b7280]">VP Score</span>
                <span className={(data.volume_profile_score ?? 0) >= 60 ? "text-emerald-400 font-bold" : "text-yellow-400 font-bold"}>
                  {(data.volume_profile_score ?? 0).toFixed(0)}/100
                </span>
              </div>
              <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
                <div className={clsx("h-full rounded-full", (data.volume_profile_score ?? 0) >= 60 ? "bg-emerald-500" : "bg-yellow-500")}
                  style={{ width: `${data.volume_profile_score ?? 0}%` }} />
              </div>
            </div>
            <div className="flex gap-1.5">
              {data.price_in_value_area && (
                <span className="text-[9px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded font-bold">IN VA</span>
              )}
              {data.near_hvn && (
                <span className="text-[9px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded font-bold">HVN</span>
              )}
              {data.near_lvn && (
                <span className="text-[9px] bg-orange-500/20 text-orange-400 border border-orange-500/30 px-1.5 py-0.5 rounded font-bold">LVN</span>
              )}
            </div>
          </div>

          {/* Key levels */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-red-400 mb-1">VAH</p>
              <p className="text-xs font-bold font-mono text-[#f9fafb]">${fmt(data.value_area_high)}</p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center border border-blue-500/20">
              <p className="text-[10px] text-blue-400 mb-1">POC</p>
              <p className="text-xs font-bold font-mono text-[#f9fafb]">${fmt(data.poc)}</p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-emerald-400 mb-1">VAL</p>
              <p className="text-xs font-bold font-mono text-[#f9fafb]">${fmt(data.value_area_low)}</p>
            </div>
          </div>

          {/* HVN / LVN */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-[#6b7280] mb-1.5 uppercase tracking-wide">HVN {data.near_hvn && "● Próximo"}</p>
              <div className="space-y-1">
                {(data.hvn_levels?.length ?? 0) === 0 && <p className="text-[10px] text-[#4b5563]">—</p>}
                {(data.hvn_levels ?? []).slice(0,4).map((lvl, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#0a0e1a] rounded px-2.5 py-1">
                    <span className="text-[10px] font-mono text-emerald-400">${fmt(lvl)}</span>
                    <span className="text-[9px] text-[#4b5563]">HVN</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[10px] text-[#6b7280] mb-1.5 uppercase tracking-wide">LVN {data.near_lvn && "● Próximo"}</p>
              <div className="space-y-1">
                {(data.lvn_levels?.length ?? 0) === 0 && <p className="text-[10px] text-[#4b5563]">—</p>}
                {(data.lvn_levels ?? []).slice(0,4).map((lvl, i) => (
                  <div key={i} className="flex items-center justify-between bg-[#0a0e1a] rounded px-2.5 py-1">
                    <span className="text-[10px] font-mono text-orange-400">${fmt(lvl)}</span>
                    <span className="text-[9px] text-[#4b5563]">LVN</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <p className="text-[10px] text-[#4b5563] text-right">
            {data.computed_at ? new Date(data.computed_at).toLocaleTimeString("pt-BR") : ""}
          </p>
        </div>
      )}
    </div>
  );
}
