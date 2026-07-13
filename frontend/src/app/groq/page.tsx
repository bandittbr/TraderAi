/**
 * TradeAI - Groq Agent Dashboard
 * Agente LLM-powered com avatar animado, thought bubbles e P&L real-time.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useWebSocket } from "@/hooks/useWebSocket";
import { AgentChart } from "@/components/dashboard/AgentChart";
import {
  getGroqAccount,
  getGroqStats,
  getGroqTrades,
  getGroqThinking,
} from "@/lib/api";
import type {
  GroqAccountResponse,
  GroqStatsResponse,
  GroqTradeResponse,
  GroqThinkingResponse,
} from "@/types";

const POLL_MS = 15_000;
type TradeFilter = "ALL" | "OPEN" | "CLOSED";

// ── Animated Avatar ──────────────────────────────────────────────────────────

function GroqAvatar({ isThinking }: { isThinking: boolean }) {
  return (
    <div className="relative w-16 h-16 flex-shrink-0">
      {/* Glow ring */}
      <div
        className={`absolute inset-0 rounded-full transition-all duration-1000 ${
          isThinking
            ? "bg-violet-500/20 animate-ping"
            : "bg-emerald-500/10"
        }`}
        style={{ transform: "scale(1.3)" }}
      />
      {/* Core avatar */}
      <div
        className={`relative w-16 h-16 rounded-full flex items-center justify-center border-2 transition-all duration-700 ${
          isThinking
            ? "border-violet-400 bg-violet-900/40 shadow-lg shadow-violet-500/20"
            : "border-emerald-400/60 bg-[#0a1020]"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className={`w-8 h-8 transition-colors duration-500 ${
            isThinking ? "text-violet-300" : "text-emerald-400"
          }`}
          fill="none"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          {/* Brain icon */}
          <path d="M12 2a7 7 0 0 0-7 7c0 2.5 1.5 4.7 3.7 5.7L7 22h10l-1.7-7.3A7 7 0 0 0 12 2z" />
          <path d="M9 9.5a3.5 3.5 0 0 1 6 0" strokeLinecap="round" />
          <circle cx="10" cy="8.5" r="0.8" fill="currentColor" />
          <circle cx="14" cy="8.5" r="0.8" fill="currentColor" />
          <path d="M12 2v2M8 5l1 1.5M16 5l-1 1.5" strokeLinecap="round" strokeWidth={1} />
        </svg>
      </div>
    </div>
  );
}

// ── Thought Bubble ───────────────────────────────────────────────────────────

function ThoughtBubble({ thinking }: { thinking: GroqThinkingResponse }) {
  const actionColor =
    thinking.action === "BUY"
      ? "text-emerald-400 bg-emerald-900/30 border-emerald-700/40"
      : thinking.action === "SELL"
      ? "text-red-400 bg-red-900/30 border-red-700/40"
      : "text-amber-400 bg-amber-900/30 border-amber-700/40";

  const hasError = !!thinking.error;

  return (
    <div
      className={`rounded-xl p-4 border transition-all duration-300 ${
        hasError
          ? "bg-red-950/20 border-red-800/30"
          : "bg-[#0d1525] border-[#1a2540] hover:border-[#2a3560]"
      }`}
    >
      <div className="flex items-center gap-3 mb-2">
        <span
          className={`px-2 py-0.5 text-[10px] font-bold rounded-md uppercase tracking-wider ${actionColor}`}
        >
          {thinking.action}
        </span>
        <span className="text-[10px] text-[#4a6080]">{thinking.symbol}</span>
        {thinking.confidence !== null && (
          <span className="text-[10px] text-[#3b5070]">
            {(thinking.confidence * 100).toFixed(0)}% conf
          </span>
        )}
        {thinking.latency_ms !== null && (
          <span className="text-[10px] text-[#3b4060] ml-auto">
            {thinking.latency_ms}ms
          </span>
        )}
      </div>
      <p className="text-xs text-[#8899bb] leading-relaxed line-clamp-3">
        {hasError ? (
          <span className="text-red-400">⚠ {thinking.error}</span>
        ) : (
          thinking.reasoning || "Sem raciocínio registrado"
        )}
      </p>
      <div className="flex items-center gap-3 mt-2 text-[10px] text-[#3b4a6b]">
        <span>{new Date(thinking.created_at).toLocaleTimeString("pt-BR")}</span>
        {thinking.prompt_tokens !== null && (
          <span>{thinking.prompt_tokens} prompt tokens</span>
        )}
        {thinking.output_tokens !== null && (
          <span>{thinking.output_tokens} output tokens</span>
        )}
      </div>
    </div>
  );
}

// ── P&L Hero ─────────────────────────────────────────────────────────────────

function PnlHero({
  account,
  stats,
}: {
  account: GroqAccountResponse;
  stats: GroqStatsResponse | null;
}) {
  const pnlPct =
    account.initial_balance > 0
      ? (account.total_pnl / account.initial_balance) * 100
      : 0;
  const isPositive = pnlPct >= 0;

  return (
    <div className="rounded-2xl bg-gradient-to-br from-[#0d1525] to-[#111d35] border border-[#1a2540] p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">
            Saldo
          </p>
          <p className="text-3xl font-bold text-white tracking-tight">
            ${account.balance.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
          <p className="text-[10px] text-[#3b4a6b] mt-1">
            Inicial: ${account.initial_balance.toLocaleString("en-US")}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] text-[#4a6080] uppercase tracking-widest mb-1">
            P&L
          </p>
          <p
            className={`text-3xl font-bold tracking-tight ${
              isPositive ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {isPositive ? "+" : ""}
            {pnlPct.toFixed(2)}%
          </p>
          <p
            className={`text-sm font-medium mt-0.5 ${
              isPositive ? "text-emerald-500/70" : "text-red-500/70"
            }`}
          >
            {isPositive ? "+" : ""}${account.total_pnl.toFixed(2)} USD
          </p>
        </div>
      </div>

      {/* Mini stats row */}
      <div className="grid grid-cols-4 gap-3 mt-5 pt-4 border-t border-[#1a2540]">
        {[
          { label: "Trades", value: account.total_trades.toString() },
          {
            label: "Win Rate",
            value:
              account.total_trades > 0
                ? `${((account.winning_trades / account.total_trades) * 100).toFixed(0)}%`
                : "—",
          },
          { label: "Wins", value: account.winning_trades.toString(), color: "text-emerald-400" },
          { label: "Losses", value: account.losing_trades.toString(), color: "text-red-400" },
        ].map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-[10px] text-[#4a6080] uppercase tracking-widest">
              {s.label}
            </p>
            <p className={`text-sm font-bold mt-0.5 ${s.color ?? "text-white"}`}>
              {s.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function GroqPage() {
  const { prices } = useWebSocket();
  const [account, setAccount] = useState<GroqAccountResponse | null>(null);
  const [stats, setStats] = useState<GroqStatsResponse | null>(null);
  const [trades, setTrades] = useState<GroqTradeResponse[]>([]);
  const [thinking, setThinking] = useState<GroqThinkingResponse[]>([]);
  const [filter, setFilter] = useState<TradeFilter>("ALL");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const [acc, st, tr, th] = await Promise.all([
      getGroqAccount(),
      getGroqStats(),
      getGroqTrades("ALL", 100),
      getGroqThinking(15),
    ]);
    setAccount(acc);
    setStats(st);
    setTrades(tr);
    setThinking(th);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const filteredTrades =
    filter === "ALL" ? trades : trades.filter((t) => t.status === filter);

  const isThinking = thinking.length > 0 && !thinking[0].error;

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-[#f9fafb]">
      {/* Header */}
      <header className="border-b border-[#1f2937] bg-[#111827]/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-[#60a5fa] hover:text-blue-300 text-sm font-medium transition-colors"
            >
              ← Dashboard
            </Link>
            <span className="text-[#1f2937]">|</span>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
              <span className="text-sm font-bold text-[#f9fafb]">Groq Agent</span>
            </div>
            <span className="text-[10px] text-[#4b5563] bg-[#1f2937] px-2 py-0.5 rounded-full">
              LLM · Llama 3.3 70B · 60s
            </span>
          </div>
          <button
            onClick={refresh}
            className="text-xs text-[#6b7280] hover:text-[#f9fafb] transition-colors px-2 py-1 rounded border border-[#1f2937] hover:border-[#374151]"
          >
            Atualizar
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">
        {/* Simulation warning */}
        <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 px-4 py-3 flex items-start gap-3">
          <span className="text-violet-400 text-base mt-0.5">🧠</span>
          <div>
            <p className="text-sm font-semibold text-violet-400">
              Groq Agent — LLM Trading 10x
            </p>
            <p className="text-xs text-[#6b7280] mt-0.5">
              Agente autônomo powered by Groq (Llama 3.3 70B). Opera com 10x de
              alavancagem em trades de 15 minutos. Usa qualquer estratégia que o
              LLM decidir. Conta virtual com $10.000 iniciais. Nenhum ativo real
              é negociado.
            </p>
          </div>
        </div>

        {/* Avatar + P&L */}
        <div className="flex items-start gap-5">
          <GroqAvatar isThinking={isThinking} />
          <div className="flex-1 min-w-0">
            {account ? (
              <PnlHero account={account} stats={stats} />
            ) : (
              <div className="h-36 rounded-2xl bg-[#111827] border border-[#1f2937] animate-pulse" />
            )}
          </div>
        </div>

        {/* Chart */}
        <AgentChart
          agent="groq"
          symbol="BTCUSDT"
          livePrice={prices["BTCUSDT"]}
          height={350}
        />

        {/* Two columns: Thinking + Trades */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Thought Bubbles */}
          <div>
            <h3 className="text-sm font-semibold text-[#f9fafb] mb-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
              Pensamentos do Groq
            </h3>
            <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1 scrollbar-thin">
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <div
                    key={i}
                    className="h-24 rounded-xl bg-[#111827] border border-[#1f2937] animate-pulse"
                  />
                ))
              ) : thinking.length === 0 ? (
                <div className="h-32 flex flex-col items-center justify-center gap-2 rounded-xl bg-[#111827] border border-[#1f2937]">
                  <p className="text-sm text-[#6b7280]">
                    Aguardando primeira análise...
                  </p>
                  <p className="text-xs text-[#4b5563]">
                    O Groq思考 a cada 60 segundos
                  </p>
                </div>
              ) : (
                thinking.map((t) => <ThoughtBubble key={t.id} thinking={t} />)
              )}
            </div>
          </div>

          {/* Trades Table */}
          <div>
            <h3 className="text-sm font-semibold text-[#f9fafb] mb-3">
              Operações
            </h3>
            {/* Filters */}
            <div className="flex gap-2 mb-3">
              {(["ALL", "OPEN", "CLOSED"] as TradeFilter[]).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1 text-xs rounded-md font-medium transition-colors border ${
                    filter === f
                      ? "bg-violet-500/20 text-violet-400 border-violet-500/30"
                      : "bg-[#111827] text-[#6b7280] border-[#1f2937] hover:text-[#f9fafb]"
                  }`}
                >
                  {f === "ALL" ? "Todos" : f === "OPEN" ? "Abertos" : "Fechados"}
                  {f !== "ALL" && (
                    <span className="ml-1 text-[10px] text-[#4b5563]">
                      ({f === "OPEN"
                        ? trades.filter((t) => t.status === "OPEN").length
                        : trades.filter((t) => t.status === "CLOSED").length})
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
              <div className="overflow-x-auto max-h-[340px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="sticky top-0 bg-[#111827]">
                    <tr className="text-[#6b7280] border-b border-[#1f2937]">
                      <th className="text-left py-2 px-3">Data</th>
                      <th className="text-center py-2 px-2">Side</th>
                      <th className="text-right py-2 px-2">Entrada</th>
                      <th className="text-right py-2 px-2">Saída</th>
                      <th className="text-right py-2 px-2">PnL</th>
                      <th className="text-right py-2 px-2">PnL %</th>
                      <th className="text-center py-2 px-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      Array.from({ length: 5 }).map((_, i) => (
                        <tr key={i} className="border-b border-[#1f2937]/50">
                          {Array.from({ length: 7 }).map((_, j) => (
                            <td key={j} className="py-3 px-2">
                              <div className="h-3 bg-[#1a2540] rounded animate-pulse" />
                            </td>
                          ))}
                        </tr>
                      ))
                    ) : filteredTrades.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-10 text-center">
                          <p className="text-sm text-[#6b7280]">
                            Nenhuma operação registrada
                          </p>
                          <p className="text-xs text-[#4b5563] mt-1">
                            Trades aparecem quando o Groq toma uma decisão de compra
                          </p>
                        </td>
                      </tr>
                    ) : (
                      filteredTrades.map((t) => {
                        const pnlColor =
                          t.status === "CLOSED"
                            ? (t.net_pnl_pct ?? 0) >= 0
                              ? "text-emerald-400"
                              : "text-red-400"
                            : "text-[#6b7280]";
                        return (
                          <tr
                            key={t.id}
                            className="border-b border-[#1f2937]/50 hover:bg-[#0d1525] transition-colors"
                          >
                            <td className="py-2 px-3 text-[#8899bb]">
                              {new Date(t.opened_at).toLocaleDateString("pt-BR", {
                                day: "2-digit",
                                month: "2-digit",
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </td>
                            <td className="py-2 px-2 text-center">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                  t.side === "BUY"
                                    ? "bg-emerald-900/40 text-emerald-400"
                                    : "bg-red-900/40 text-red-400"
                                }`}
                              >
                                {t.side}
                              </span>
                            </td>
                            <td className="py-2 px-2 text-right text-white font-mono">
                              ${t.entry_price.toFixed(2)}
                            </td>
                            <td className="py-2 px-2 text-right text-[#6b7280] font-mono">
                              {t.exit_price ? `$${t.exit_price.toFixed(2)}` : "—"}
                            </td>
                            <td className={`py-2 px-2 text-right font-mono ${pnlColor}`}>
                              {t.pnl !== null
                                ? `${t.pnl >= 0 ? "+" : ""}$${t.pnl.toFixed(2)}`
                                : "—"}
                            </td>
                            <td className={`py-2 px-2 text-right font-mono ${pnlColor}`}>
                              {t.net_pnl_pct !== null
                                ? `${t.net_pnl_pct >= 0 ? "+" : ""}${t.net_pnl_pct.toFixed(2)}%`
                                : "—"}
                            </td>
                            <td className="py-2 px-2 text-center">
                              {t.status === "OPEN" ? (
                                <span className="inline-flex items-center gap-1 text-[10px] text-violet-400">
                                  <span className="w-1 h-1 rounded-full bg-violet-400 animate-pulse" />
                                  Aberto
                                </span>
                              ) : (
                                <span className="text-[10px] text-[#4b5563]">
                                  {t.close_reason || "Fechado"}
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        {/* Debug strip */}
        <div className="rounded-xl bg-[#0d1525] border border-[#1a2540] px-4 py-3 flex items-center gap-6 text-[10px] text-[#3b4a6b]">
          <span>
            Modelo: <span className="text-violet-400">llama-3.3-70b-versatile</span>
          </span>
          <span>
            Alavancagem: <span className="text-violet-400">10x</span>
          </span>
          <span>
            Timeframe: <span className="text-violet-400">15min</span>
          </span>
          <span>
            Free tier: <span className="text-violet-400">1000 RPD</span>
          </span>
          <span>
            Max risk: <span className="text-violet-400">2%/trade</span>
          </span>
        </div>
      </main>

      <footer className="border-t border-[#1f2937] mt-8 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <p className="text-xs text-center text-[#4b5563]">
            TradeAI · Groq Agent · LLM-Powered Trading · Conta Virtual
          </p>
        </div>
      </footer>
    </div>
  );
}
