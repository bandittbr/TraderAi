"use client";

import { useState } from "react";
import { runBacktest } from "@/lib/api";
import type { BacktestResultResponse } from "@/types";
import { clsx } from "clsx";

const SYMBOLS  = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const PERIODS  = [7, 30, 90, 180];

function MetricBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="bg-[#0a0e1a] rounded-lg p-3 text-center">
      <p className="text-xs text-[#6b7280] mb-1">{label}</p>
      <p className={`text-base font-bold ${color ?? "text-[#f9fafb]"}`}>{value}</p>
    </div>
  );
}

export function BacktestPanel() {
  const [symbol,  setSymbol]  = useState("BTCUSDT");
  const [period,  setPeriod]  = useState(30);
  const [loading, setLoading] = useState(false);
  const [result,  setResult]  = useState<BacktestResultResponse | null>(null);
  const [error,   setError]   = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    const res = await runBacktest(symbol, period);
    if (res) {
      setResult(res);
    } else {
      setError("Falha ao executar backtest. Verifique se há candles históricos no banco.");
    }
    setLoading(false);
  }

  return (
    <div className="bg-[#111827] border border-[#1f2937] rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[#f9fafb]">Backtest</h3>
        <span className="text-xs text-[#4b5563]">Dados históricos do banco</span>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end">
        {/* Símbolo */}
        <div>
          <p className="text-xs text-[#6b7280] mb-1">Ativo</p>
          <div className="flex gap-1">
            {SYMBOLS.map((s) => (
              <button
                key={s}
                onClick={() => setSymbol(s)}
                className={clsx(
                  "px-2.5 py-1 text-xs rounded-md font-medium transition-colors border",
                  symbol === s
                    ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                    : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-[#f9fafb]",
                )}
              >
                {s.replace("USDT", "")}
              </button>
            ))}
          </div>
        </div>

        {/* Período */}
        <div>
          <p className="text-xs text-[#6b7280] mb-1">Período</p>
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={clsx(
                  "px-2.5 py-1 text-xs rounded-md font-medium transition-colors border",
                  period === p
                    ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                    : "bg-[#1f2937] text-[#9ca3af] border-transparent hover:text-[#f9fafb]",
                )}
              >
                {p}d
              </button>
            ))}
          </div>
        </div>

        {/* Botão */}
        <button
          onClick={handleRun}
          disabled={loading}
          className="px-4 py-1.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading && (
            <span className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin" />
          )}
          {loading ? "Executando..." : "Executar Backtest"}
        </button>
      </div>

      {/* Erro */}
      {error && (
        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Resultado */}
      {result && !loading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-xs text-[#6b7280]">
              {result.symbol.replace("USDT","")} · {result.period_days}d · {result.candles_used} candles
            </p>
            <p className="text-xs text-[#4b5563]">
              {new Date(result.finished_at).toLocaleTimeString("pt-BR")}
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <MetricBox
              label="Trades"
              value={String(result.total_trades)}
            />
            <MetricBox
              label="Win Rate"
              value={`${result.win_rate.toFixed(1)}%`}
              color={result.win_rate >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
            <MetricBox
              label="PnL Total"
              value={`${result.total_pnl >= 0 ? "+" : ""}$${result.total_pnl.toFixed(2)}`}
              color={result.total_pnl >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
            <MetricBox
              label="Max Drawdown"
              value={`${result.max_drawdown.toFixed(2)}%`}
              color={result.max_drawdown > 10 ? "text-[#ef4444]" : "text-[#f59e0b]"}
            />
            <MetricBox
              label="Profit Factor"
              value={result.profit_factor === 0 ? "N/A" : result.profit_factor.toFixed(2)}
              color={result.profit_factor >= 1 ? "text-[#10b981]" : "text-[#ef4444]"}
            />
            <MetricBox
              label="Ganho Médio"
              value={`$${result.avg_gain.toFixed(2)}`}
              color="text-[#10b981]"
            />
            <MetricBox
              label="Perda Média"
              value={`$${result.avg_loss.toFixed(2)}`}
              color="text-[#ef4444]"
            />
            <MetricBox
              label="Wins / Losses"
              value={`${result.winning_trades} / ${result.losing_trades}`}
            />
          </div>

          {/* LONG vs SHORT comparativo */}
          {((result.long_trades ?? 0) + (result.short_trades ?? 0)) > 0 && (
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-[#0a0e1a] rounded-lg p-3 border border-emerald-500/15">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-emerald-400">▲ LONG</span>
                  <span className="text-[10px] text-[#4b5563]">{result.long_trades ?? 0} trades</span>
                </div>
                <div className="flex gap-3 text-xs">
                  <span className="text-[#6b7280]">WR</span>
                  <span className={`font-semibold ${(result.win_rate_long ?? 0) >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                    {(result.win_rate_long ?? 0).toFixed(1)}%
                  </span>
                  <span className="text-[#6b7280]">PnL</span>
                  <span className={`font-semibold ${(result.pnl_long ?? 0) >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                    ${(result.pnl_long ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>
              <div className="bg-[#0a0e1a] rounded-lg p-3 border border-red-500/15">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-bold text-red-400">▼ SHORT</span>
                  <span className="text-[10px] text-[#4b5563]">{result.short_trades ?? 0} trades</span>
                </div>
                <div className="flex gap-3 text-xs">
                  <span className="text-[#6b7280]">WR</span>
                  <span className={`font-semibold ${(result.win_rate_short ?? 0) >= 50 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                    {(result.win_rate_short ?? 0).toFixed(1)}%
                  </span>
                  <span className="text-[#6b7280]">PnL</span>
                  <span className={`font-semibold ${(result.pnl_short ?? 0) >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                    ${(result.pnl_short ?? 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Mini lista de trades */}
          {result.trades.length > 0 && (
            <div className="max-h-48 overflow-y-auto rounded-lg border border-[#1f2937]">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-[#0a0e1a]">
                  <tr className="text-[#6b7280] border-b border-[#1f2937]">
                    <th className="text-center py-1.5 px-2">Side</th>
                    <th className="text-left py-1.5 px-3">Entrada</th>
                    <th className="text-right py-1.5 px-3">Saída</th>
                    <th className="text-right py-1.5 px-3">PnL %</th>
                    <th className="text-center py-1.5 px-3">Motivo</th>
                    <th className="text-center py-1.5 px-3">Res.</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={i} className="border-b border-[#1f2937]/40">
                      <td className="py-1.5 px-2 text-center">
                        <span className={`text-[10px] font-bold ${
                          (t.side ?? "LONG") === "LONG" ? "text-emerald-400" : "text-red-400"
                        }`}>
                          {(t.side ?? "LONG") === "LONG" ? "▲" : "▼"}{t.side ?? "LONG"}
                        </span>
                      </td>
                      <td className="py-1.5 px-3 text-[#9ca3af]">${t.entry_price.toFixed(2)}</td>
                      <td className="py-1.5 px-3 text-right text-[#9ca3af]">${t.exit_price.toFixed(2)}</td>
                      <td className={`py-1.5 px-3 text-right ${t.pnl_pct >= 0 ? "text-[#10b981]" : "text-[#ef4444]"}`}>
                        {t.pnl_pct >= 0 ? "+" : ""}{t.pnl_pct.toFixed(2)}%
                      </td>
                      <td className="py-1.5 px-3 text-center text-[#6b7280] text-[10px]">
                        {t.close_reason.replace("_"," ")}
                      </td>
                      <td className="py-1.5 px-3 text-center">
                        <span className={`text-[10px] font-semibold ${
                          t.result === "WIN" ? "text-[#10b981]" : "text-[#ef4444]"
                        }`}>
                          {t.result}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
