"use client";

import { useState } from "react";

interface SignalRecord {
  id: number;
  symbol: string;
  signal: string;
  confidence: number;
  regime: string;
  rsi: number | null;
  ema_alignment: string | null;
  criteria_count: number | null;
  context_boost: number;
  outcome: string;
  pnl_pct: number | null;
  trade_duration_min: number | null;
  exit_reason: string | null;
  emitted_at: string;
}

const SIGNAL_COLORS: Record<string, string> = {
  BUY:     "text-green-400 bg-green-900/20",
  SELL:    "text-red-400 bg-red-900/20",
  NEUTRAL: "text-yellow-400 bg-yellow-900/20",
};

const OUTCOME_COLORS: Record<string, string> = {
  WIN:    "text-green-400",
  LOSS:   "text-red-400",
  OPEN:   "text-blue-400",
  MISSED: "text-gray-500",
};

const REGIME_LABELS: Record<string, string> = {
  BULL:            "Bull",
  BEAR:            "Bear",
  SIDEWAYS:        "Lateral",
  HIGH_VOLATILITY: "Alt Vol",
  UNKNOWN:         "—",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function formatDuration(min: number | null): string {
  if (min === null) return "—";
  if (min < 60) return `${min}m`;
  return `${Math.floor(min / 60)}h${min % 60 > 0 ? ` ${min % 60}m` : ""}`;
}

interface Props {
  signals: SignalRecord[];
  loading?: boolean;
}

export function SignalHistoryTable({ signals, loading }: Props) {
  const [filter, setFilter] = useState<"ALL" | "BUY" | "SELL" | "WIN" | "LOSS">("ALL");

  const filtered = signals.filter((s) => {
    if (filter === "ALL")  return true;
    if (filter === "BUY")  return s.signal === "BUY";
    if (filter === "SELL") return s.signal === "SELL";
    if (filter === "WIN")  return s.outcome === "WIN";
    if (filter === "LOSS") return s.outcome === "LOSS";
    return true;
  });

  return (
    <div className="bg-gray-900 rounded-lg border border-gray-800">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h3 className="text-sm font-medium text-gray-300">Histórico de Sinais</h3>
        <div className="flex gap-1">
          {(["ALL", "BUY", "SELL", "WIN", "LOSS"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center text-gray-500 py-8 text-sm">Carregando...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-600 py-8 text-sm">
          Nenhum sinal registrado ainda.
          <br />
          <span className="text-xs">Os sinais aparecem após o primeiro ciclo de indicadores.</span>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-500 border-b border-gray-800">
                <th className="text-left px-3 py-2">Data</th>
                <th className="text-left px-3 py-2">Ativo</th>
                <th className="text-center px-3 py-2">Sinal</th>
                <th className="text-right px-3 py-2">Conf%</th>
                <th className="text-center px-3 py-2">Regime</th>
                <th className="text-right px-3 py-2">RSI</th>
                <th className="text-right px-3 py-2">Critérios</th>
                <th className="text-right px-3 py-2">Boost</th>
                <th className="text-center px-3 py-2">Resultado</th>
                <th className="text-right px-3 py-2">PnL%</th>
                <th className="text-right px-3 py-2">Duração</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                  <td className="px-3 py-2 text-gray-400 whitespace-nowrap">
                    {formatDate(s.emitted_at)}
                  </td>
                  <td className="px-3 py-2 font-medium text-white">
                    {s.symbol.replace("USDT", "")}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`px-1.5 py-0.5 rounded text-xs font-semibold ${SIGNAL_COLORS[s.signal] ?? ""}`}>
                      {s.signal}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right text-white">{s.confidence.toFixed(0)}%</td>
                  <td className="px-3 py-2 text-center text-gray-400">
                    {REGIME_LABELS[s.regime] ?? s.regime}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-300">
                    {s.rsi !== null ? s.rsi.toFixed(1) : "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-400">
                    {s.criteria_count ?? "—"}
                  </td>
                  <td className={`px-3 py-2 text-right font-semibold ${s.context_boost > 0 ? "text-green-400" : s.context_boost < 0 ? "text-red-400" : "text-gray-500"}`}>
                    {s.context_boost > 0 ? "+" : ""}{s.context_boost}
                  </td>
                  <td className={`px-3 py-2 text-center font-semibold ${OUTCOME_COLORS[s.outcome] ?? "text-gray-400"}`}>
                    {s.outcome}
                  </td>
                  <td className={`px-3 py-2 text-right font-semibold ${
                    s.pnl_pct === null ? "text-gray-500" :
                    s.pnl_pct >= 0 ? "text-green-400" : "text-red-400"
                  }`}>
                    {s.pnl_pct !== null ? `${s.pnl_pct >= 0 ? "+" : ""}${s.pnl_pct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-400">
                    {formatDuration(s.trade_duration_min)}
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
