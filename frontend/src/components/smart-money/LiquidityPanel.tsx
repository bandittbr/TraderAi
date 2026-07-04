"use client";

import { useEffect, useState, useCallback } from "react";
import { clsx } from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SYMBOLS    = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const TIMEFRAMES = ["15m", "1h", "4h"];

interface SmartMoneyData {
  symbol: string; timeframe: string;
  has_recent_buy_sweep: boolean; has_recent_sell_sweep: boolean;
  sweep_bias: string; last_sweep_type: string | null; last_sweep_price: number | null;
  has_bullish_fvg: boolean; has_bearish_fvg: boolean;
  bullish_fvg_top: number | null; bullish_fvg_bottom: number | null; bullish_fvg_distance_pct: number;
  bearish_fvg_top: number | null; bearish_fvg_bottom: number | null; bearish_fvg_distance_pct: number;
  volume_profile_score: number; poc: number | null;
  value_area_high: number | null; value_area_low: number | null;
  hvn_levels: number[]; lvn_levels: number[];
  near_hvn: boolean; near_lvn: boolean; price_in_value_area: boolean;
  liquidity_score: number; liquidity_label: string; liq_score_strong: boolean;
  recent_sweeps: { type: string; strength: string; price: number; swept_level: number; timestamp: number; penetration_pct: number; is_stop_hunt: boolean }[];
  active_fvgs: { type: string; status: string; gap_top: number; gap_bottom: number; gap_size_pct: number; distance_pct: number; relevance: number; is_filled: boolean }[];
  candles_analyzed: number; computed_at: string | null;
}

function fmt(n: number | null | undefined, dec = 2) {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 80 ? "bg-emerald-500" :
    score >= 60 ? "bg-blue-500" :
    score >= 40 ? "bg-yellow-500" :
    score >= 20 ? "bg-orange-500" : "bg-red-500";
  const textColor =
    score >= 60 ? "text-emerald-400" : score >= 40 ? "text-yellow-400" : "text-red-400";
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] text-[#6b7280]">Liquidity Score</span>
        <span className={`text-xs font-bold ${textColor}`}>{score.toFixed(0)}/100 · {label}</span>
      </div>
      <div className="h-1.5 bg-[#1f2937] rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${score}%` }} />
      </div>
    </div>
  );
}

export function LiquidityPanel() {
  const [symbol,    setSymbol]    = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [data,      setData]      = useState<SmartMoneyData | null>(null);
  const [loading,   setLoading]   = useState(false);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API_BASE}/smc/${symbol}?timeframe=${timeframe}`);
      if (r.ok) setData(await r.json());
    } catch { /* noop */ } finally { setLoading(false); }
  }, [symbol, timeframe]);

  useEffect(() => { fetch_(); const id = setInterval(fetch_, 60_000); return () => clearInterval(id); }, [fetch_]);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Liquidity Panel</h3>
          <p className="text-[10px] text-[#4b5563] mt-0.5">Sweeps · FVGs · Volume Profile · Score</p>
        </div>
        <button onClick={fetch_} disabled={loading} className="text-xs text-[#6b7280] hover:text-white disabled:opacity-40">
          {loading ? "..." : "↻"}
        </button>
      </div>

      {/* Controls */}
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
        <div className="h-32 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {data && (
        <div className="space-y-3">
          {/* Score bar */}
          <ScoreBar score={data.liquidity_score} label={data.liquidity_label} />

          {/* Quick flags */}
          <div className="flex flex-wrap gap-1.5">
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.has_recent_buy_sweep
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.has_recent_buy_sweep ? "● " : "○ "}Buy Sweep
            </span>
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.has_recent_sell_sweep
                ? "bg-red-500/20 text-red-400 border-red-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.has_recent_sell_sweep ? "● " : "○ "}Sell Sweep
            </span>
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.has_bullish_fvg
                ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.has_bullish_fvg ? "● " : "○ "}Bull FVG
            </span>
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.has_bearish_fvg
                ? "bg-red-500/20 text-red-400 border-red-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.has_bearish_fvg ? "● " : "○ "}Bear FVG
            </span>
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.near_hvn
                ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.near_hvn ? "● " : "○ "}HVN
            </span>
            <span className={clsx("px-2 py-0.5 rounded text-[10px] font-bold border",
              data.price_in_value_area
                ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                : "bg-transparent text-[#4b5563] border-[#1f2937]")}>
              {data.price_in_value_area ? "● " : "○ "}In VA
            </span>
          </div>

          {/* Volume Profile key levels */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280] mb-1">POC</p>
              <p className="text-xs font-bold font-mono text-[#f9fafb]">${fmt(data.poc)}</p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280] mb-1">VAH</p>
              <p className="text-xs font-bold font-mono text-red-400">${fmt(data.value_area_high)}</p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280] mb-1">VAL</p>
              <p className="text-xs font-bold font-mono text-emerald-400">${fmt(data.value_area_low)}</p>
            </div>
          </div>

          {/* VP score + bias */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280] mb-1">VP Score</p>
              <p className={`text-sm font-bold ${(data.volume_profile_score ?? 0) >= 60 ? "text-emerald-400" : "text-yellow-400"}`}>
                {(data.volume_profile_score ?? 0).toFixed(0)}
              </p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
              <p className="text-[10px] text-[#6b7280] mb-1">Sweep Bias</p>
              <p className={`text-sm font-bold ${
                (data.sweep_bias ?? "") === "BULLISH" ? "text-emerald-400" :
                (data.sweep_bias ?? "") === "BEARISH" ? "text-red-400" : "text-[#6b7280]"
              }`}>{data.sweep_bias ?? "—"}</p>
            </div>
          </div>

          <p className="text-[10px] text-[#4b5563] text-right">
            {data.candles_analyzed ?? 0}c · {data.computed_at ? new Date(data.computed_at).toLocaleTimeString("pt-BR") : ""}
          </p>
        </div>
      )}
    </div>
  );
}
