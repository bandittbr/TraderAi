"use client";

import { useEffect, useState, useCallback } from "react";
import { clsx } from "clsx";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const SYMBOLS    = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

interface SRZone {
  level:       number;
  zone_type:   "SUPPORT" | "RESISTANCE";
  touch_count: number;
  strength:    "WEAK" | "MODERATE" | "STRONG";
  range_low:   number;
  range_high:  number;
}

interface StructureData {
  symbol:     string;
  timeframe:  string;
  trend:      string;
  confidence: number;
  structure_label: string;
  last_swing_high: number | null;
  last_swing_low:  number | null;
  last_high_label: string | null;
  last_low_label:  string | null;
  hh_count: number; hl_count: number;
  lh_count: number; ll_count: number;
  bos_bullish: boolean; bos_bearish: boolean;
  bos_level: number | null; is_choch: boolean; bos_strength: number;
  nearest_support: number | null; nearest_resistance: number | null;
  price_near_support: boolean; price_near_resistance: boolean;
  support_distance_pct: number; resistance_distance_pct: number;
  support_zones: SRZone[]; resistance_zones: SRZone[];
  candles_analyzed: number; computed_at: string | null; reasons: string[];
}

function fmt(n: number | null | undefined, dec = 2) {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function TrendBadge({ trend }: { trend: string }) {
  const cfg: Record<string, { color: string; icon: string }> = {
    BULLISH:   { color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30", icon: "▲" },
    BEARISH:   { color: "bg-red-500/20 text-red-400 border-red-500/30",             icon: "▼" },
    RANGING:   { color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",    icon: "↔" },
    UNDEFINED: { color: "bg-gray-500/20 text-gray-400 border-gray-500/30",          icon: "?" },
  };
  const { color, icon } = cfg[trend] ?? cfg["UNDEFINED"];
  return <span className={`px-2.5 py-1 rounded-md border text-xs font-bold ${color}`}>{icon} {trend}</span>;
}

function StrengthDot({ strength }: { strength?: string | null }) {
  const s = strength ?? "";
  return <span className={clsx(
    "text-[10px] font-semibold",
    s === "STRONG" ? "text-emerald-400" : s === "MODERATE" ? "text-yellow-400" : "text-gray-600",
  )}>{s || "—"}</span>;
}

export function MarketStructurePanel() {
  const [symbol,    setSymbol]    = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("1h");
  const [data,      setData]      = useState<StructureData | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState<string | null>(null);

  const fetchStructure = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API_BASE}/structure/${symbol}?timeframe=${timeframe}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally { setLoading(false); }
  }, [symbol, timeframe]);

  useEffect(() => {
    fetchStructure();
    const id = setInterval(fetchStructure, 60_000);
    return () => clearInterval(id);
  }, [fetchStructure]);

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-[#f9fafb]">Market Structure</h3>
          <p className="text-[10px] text-[#4b5563] mt-0.5">HH/HL/LH/LL · BOS/CHoCH · S/R Zones</p>
        </div>
        <button onClick={fetchStructure} disabled={loading}
          className="text-xs text-[#6b7280] hover:text-white disabled:opacity-40 transition-colors">
          {loading ? "..." : "↻ Atualizar"}
        </button>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1">
          {SYMBOLS.map(s => (
            <button key={s} onClick={() => setSymbol(s)}
              className={clsx("px-2.5 py-1 text-xs rounded-md font-medium border transition-colors",
                symbol === s ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                             : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-white")}>
              {s.replace("USDT", "")}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {TIMEFRAMES.map(tf => (
            <button key={tf} onClick={() => setTimeframe(tf)}
              className={clsx("px-2.5 py-1 text-xs rounded-md font-medium border transition-colors",
                timeframe === tf ? "bg-purple-500/20 text-purple-400 border-purple-500/30"
                                 : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-white")}>
              {tf}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {loading && !data && (
        <div className="h-40 flex items-center justify-center">
          <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {data && (
        <div className="space-y-3">
          {/* Trend row */}
          <div className="flex items-center gap-2 flex-wrap">
            <TrendBadge trend={data.trend} />
            <span className="text-xs text-[#6b7280]">{data.structure_label}</span>
            <span className="text-xs text-[#4b5563]">{(data.confidence ?? 0).toFixed(0)}% · {data.candles_analyzed}c</span>
            {data.bos_bullish && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">BOS ▲</span>
            )}
            {data.bos_bearish && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/30">BOS ▼</span>
            )}
            {data.is_choch && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/15 text-orange-400 border border-orange-500/30">CHoCH</span>
            )}
          </div>

          {/* HH/HL/LH/LL */}
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: "HH", count: data.hh_count, color: "text-emerald-400" },
              { label: "HL", count: data.hl_count, color: "text-emerald-300" },
              { label: "LH", count: data.lh_count, color: "text-red-300" },
              { label: "LL", count: data.ll_count, color: "text-red-400" },
            ].map(({ label, count, color }) => (
              <div key={label} className="bg-[#0a0e1a] rounded-lg p-2.5 text-center">
                <p className={`text-base font-bold ${color}`}>{count}</p>
                <p className="text-[10px] text-[#6b7280]">{label}</p>
              </div>
            ))}
          </div>

          {/* Last swings */}
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-[#0a0e1a] rounded-lg p-3 border border-emerald-500/10">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#6b7280]">Último Topo</span>
                {data.last_high_label && (
                  <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded border",
                    data.last_high_label === "HH"
                      ? "text-emerald-400 border-emerald-500/30"
                      : "text-red-400 border-red-500/30")}>
                    {data.last_high_label}
                  </span>
                )}
              </div>
              <p className="text-sm font-bold font-mono text-[#f9fafb]">${fmt(data.last_swing_high)}</p>
            </div>
            <div className="bg-[#0a0e1a] rounded-lg p-3 border border-red-500/10">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-[#6b7280]">Último Fundo</span>
                {data.last_low_label && (
                  <span className={clsx("text-[10px] font-bold px-1.5 py-0.5 rounded border",
                    data.last_low_label === "HL"
                      ? "text-emerald-400 border-emerald-500/30"
                      : "text-red-400 border-red-500/30")}>
                    {data.last_low_label}
                  </span>
                )}
              </div>
              <p className="text-sm font-bold font-mono text-[#f9fafb]">${fmt(data.last_swing_low)}</p>
            </div>
          </div>

          {/* SR Zones */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] text-[#6b7280] mb-1.5 uppercase tracking-wide">Resistências</p>
              <div className="space-y-1">
                {(data.resistance_zones?.length ?? 0) === 0 && <p className="text-[10px] text-[#4b5563]">Nenhuma</p>}
                {(data.resistance_zones ?? []).slice(0, 4).map((z, i) => (
                  <div key={i} className={clsx(
                    "flex items-center justify-between px-2.5 py-1.5 rounded-md",
                    data.price_near_resistance && i === 0
                      ? "bg-red-500/15 border border-red-500/30"
                      : "bg-[#0a0e1a]",
                  )}>
                    <span className="text-xs font-mono text-[#f9fafb]">${fmt(z.level)}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-[#6b7280]">×{z.touch_count}</span>
                      <StrengthDot strength={z.strength} />
                    </div>
                  </div>
                ))}
                {data.price_near_resistance && (
                  <p className="text-[10px] text-red-400">↑ Próximo (+{(data.resistance_distance_pct ?? 0).toFixed(2)}%)</p>
                )}
              </div>
            </div>

            <div>
              <p className="text-[10px] text-[#6b7280] mb-1.5 uppercase tracking-wide">Suportes</p>
              <div className="space-y-1">
                {(data.support_zones?.length ?? 0) === 0 && <p className="text-[10px] text-[#4b5563]">Nenhum</p>}
                {(data.support_zones ?? []).slice(0, 4).map((z, i) => (
                  <div key={i} className={clsx(
                    "flex items-center justify-between px-2.5 py-1.5 rounded-md",
                    data.price_near_support && i === 0
                      ? "bg-emerald-500/15 border border-emerald-500/30"
                      : "bg-[#0a0e1a]",
                  )}>
                    <span className="text-xs font-mono text-[#f9fafb]">${fmt(z.level)}</span>
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-[#6b7280]">×{z.touch_count}</span>
                      <StrengthDot strength={z.strength} />
                    </div>
                  </div>
                ))}
                {data.price_near_support && (
                  <p className="text-[10px] text-emerald-400">↓ Próximo (-{(data.support_distance_pct ?? 0).toFixed(2)}%)</p>
                )}
              </div>
            </div>
          </div>

          {/* BOS detail */}
          {(data.bos_bullish || data.bos_bearish) && data.bos_level && (
            <div className={clsx("rounded-lg p-3 border text-xs",
              data.bos_bullish ? "bg-emerald-500/10 border-emerald-500/20" : "bg-red-500/10 border-red-500/20")}>
              <span className={data.bos_bullish ? "text-emerald-400" : "text-red-400"}>
                {data.is_choch ? "CHoCH" : "BOS"} {data.bos_bullish ? "Bullish" : "Bearish"}:
              </span>{" "}
              <span className="text-[#f9fafb] font-mono">${fmt(data.bos_level)}</span>
              {data.bos_strength > 0 && (
                <span className="text-[#6b7280] ml-2">força {(data.bos_strength ?? 0).toFixed(2)}%</span>
              )}
            </div>
          )}

          <p className="text-[10px] text-[#4b5563] text-right">
            {data.computed_at ? new Date(data.computed_at).toLocaleTimeString("pt-BR") : ""}
          </p>
        </div>
      )}
    </div>
  );
}
