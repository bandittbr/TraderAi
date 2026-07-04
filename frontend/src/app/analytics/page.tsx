"use client";

import { useEffect, useState, useCallback } from "react";
import { RegimeIndicator } from "@/components/analytics/RegimeIndicator";
import { SignalHistoryTable } from "@/components/analytics/SignalHistoryTable";
import { MetricsDashboard } from "@/components/analytics/MetricsDashboard";
import { StrategyAnalyticsPanel } from "@/components/analytics/StrategyAnalyticsPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
const SYMBOLS  = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];
const PERIODS  = [7, 14, 30, 60];

type RegimeData   = Awaited<ReturnType<typeof fetchRegime>>;
type MetricsData  = Awaited<ReturnType<typeof fetchMetrics>>;
type StrategyData = Awaited<ReturnType<typeof fetchStrategy>>;
type SignalData   = Awaited<ReturnType<typeof fetchSignals>>;

async function fetchRegime(symbol: string) {
  const r = await fetch(`${API_BASE}/analytics/regime/${symbol}`);
  if (!r.ok) return null;
  return r.json();
}

async function fetchMetrics(symbol: string | null, period: number) {
  const params = new URLSearchParams({ period_days: String(period) });
  if (symbol) params.append("symbol", symbol);
  const r = await fetch(`${API_BASE}/analytics/metrics?${params}`);
  if (!r.ok) return null;
  return r.json();
}

async function fetchStrategy(symbol: string | null, period: number) {
  const params = new URLSearchParams({ period_days: String(period) });
  if (symbol) params.append("symbol", symbol);
  const r = await fetch(`${API_BASE}/analytics/strategy?${params}`);
  if (!r.ok) return null;
  return r.json();
}

async function fetchSignals(symbol: string | null, period: number) {
  const params = new URLSearchParams({ period_days: String(period), limit: "200" });
  if (symbol) params.append("symbol", symbol);
  const r = await fetch(`${API_BASE}/analytics/signals?${params}`);
  if (!r.ok) return null;
  return r.json();
}

export default function AnalyticsPage() {
  const [activeSymbol, setActiveSymbol] = useState<string | null>(null);
  const [activePeriod, setActivePeriod] = useState<number>(30);
  const [loading, setLoading]           = useState(false);

  const [regimeData,   setRegimeData]   = useState<RegimeData>(null);
  const [metricsData,  setMetricsData]  = useState<MetricsData>(null);
  const [strategyData, setStrategyData] = useState<StrategyData>(null);
  const [signalData,   setSignalData]   = useState<SignalData>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [regime, metrics, strategy, signals] = await Promise.all([
        activeSymbol ? fetchRegime(activeSymbol) : Promise.resolve(null),
        fetchMetrics(activeSymbol, activePeriod),
        fetchStrategy(activeSymbol, activePeriod),
        fetchSignals(activeSymbol, activePeriod),
      ]);
      setRegimeData(regime);
      setMetricsData(metrics);
      setStrategyData(strategy);
      setSignalData(signals);
    } catch {
      // silenciar erros de conectividade
    } finally {
      setLoading(false);
    }
  }, [activeSymbol, activePeriod]);

  useEffect(() => {
    load();
    const interval = setInterval(load, 60_000);
    return () => clearInterval(interval);
  }, [load]);

  const signals = signalData?.signals ?? [];

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-white">Signal Analytics</h1>
            <p className="text-sm text-gray-500 mt-0.5">
              Performance histórica · Regime de mercado · Análise estratégica
            </p>
          </div>
          <a
            href="/"
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            ← Dashboard
          </a>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap gap-3 mb-6">
          {/* Seletor de ativo */}
          <div className="flex gap-1 bg-gray-900 rounded-lg p-1 border border-gray-800">
            <button
              onClick={() => setActiveSymbol(null)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                activeSymbol === null ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
              }`}
            >
              Todos
            </button>
            {SYMBOLS.map((s) => (
              <button
                key={s}
                onClick={() => setActiveSymbol(s)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activeSymbol === s ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                {s.replace("USDT", "")}
              </button>
            ))}
          </div>

          {/* Seletor de período */}
          <div className="flex gap-1 bg-gray-900 rounded-lg p-1 border border-gray-800">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setActivePeriod(p)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activePeriod === p ? "bg-purple-600 text-white" : "text-gray-400 hover:text-white"
                }`}
              >
                {p}d
              </button>
            ))}
          </div>

          {/* Botão de refresh */}
          <button
            onClick={load}
            disabled={loading}
            className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white text-xs rounded-lg border border-gray-700 transition-colors disabled:opacity-50"
          >
            {loading ? "Atualizando..." : "↻ Atualizar"}
          </button>
        </div>

        {/* Grid principal */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          {/* Regime */}
          <div>
            <RegimeIndicator data={regimeData} />
          </div>

          {/* Métricas */}
          <div className="lg:col-span-2">
            <MetricsDashboard
              metrics={metricsData}
              loading={loading && !metricsData}
            />
          </div>
        </div>

        {/* Strategy Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
          <div className="lg:col-span-1">
            <StrategyAnalyticsPanel
              data={strategyData}
              loading={loading && !strategyData}
            />
          </div>

          {/* Resumo + LONG vs SHORT */}
          <div className="lg:col-span-2 space-y-4">
            {/* Métricas gerais */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-3">Resumo Geral</h3>
              {strategyData ? (
                <div className="grid grid-cols-2 gap-3">
                  <StatBlock label="Sinais Totais"   value={String(strategyData.total_signals)}            color="text-gray-300" />
                  <StatBlock label="Resolvidos"       value={String(strategyData.resolved_signals)}          color="text-gray-300" />
                  <StatBlock label="Compras (BUY)"   value={String(strategyData.buy_signals)}               color="text-green-400" />
                  <StatBlock label="Vendas (SELL)"   value={String(strategyData.sell_signals)}              color="text-red-400" />
                  <StatBlock label="Win Rate"         value={`${strategyData.win_rate.toFixed(1)}%`}         color={strategyData.win_rate >= 55 ? "text-green-400" : "text-yellow-400"} />
                  <StatBlock label="Profit Factor"   value={strategyData.profit_factor.toFixed(2)}          color={strategyData.profit_factor >= 1.5 ? "text-green-400" : "text-yellow-400"} />
                  <StatBlock label="Expectância/trade" value={`${strategyData.expectancy >= 0 ? "+" : ""}${strategyData.expectancy.toFixed(2)}%`}
                    color={strategyData.expectancy > 0 ? "text-green-400" : "text-red-400"} />
                  <StatBlock label="Sharpe Ratio"    value={strategyData.sharpe_ratio.toFixed(2)}           color={strategyData.sharpe_ratio >= 1.5 ? "text-green-400" : "text-yellow-400"} />
                </div>
              ) : (
                <div className="text-center text-gray-600 py-8 text-sm">Sem dados</div>
              )}
            </div>

            {/* LONG vs SHORT comparativo */}
            <div className="bg-gray-900 rounded-lg border border-gray-800 p-4">
              <h3 className="text-sm font-medium text-gray-400 mb-3">LONG vs SHORT</h3>
              {strategyData && ((strategyData.long_trades ?? 0) + (strategyData.short_trades ?? 0)) > 0 ? (
                <div className="grid grid-cols-2 gap-3">
                  {/* LONG */}
                  <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-emerald-400">▲ LONG</span>
                      <span className="text-[10px] text-gray-500">{strategyData.long_trades ?? 0} trades</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">Win Rate</span>
                        <span className={`font-semibold ${(strategyData.win_rate_long ?? 0) >= 50 ? "text-emerald-400" : "text-red-400"}`}>
                          {(strategyData.win_rate_long ?? 0).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">Profit Factor</span>
                        <span className={`font-semibold ${(strategyData.pf_long ?? 0) >= 1.2 ? "text-emerald-400" : "text-yellow-400"}`}>
                          {(strategyData.pf_long ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* SHORT */}
                  <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-bold text-red-400">▼ SHORT</span>
                      <span className="text-[10px] text-gray-500">{strategyData.short_trades ?? 0} trades</span>
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">Win Rate</span>
                        <span className={`font-semibold ${(strategyData.win_rate_short ?? 0) >= 50 ? "text-emerald-400" : "text-red-400"}`}>
                          {(strategyData.win_rate_short ?? 0).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between text-xs">
                        <span className="text-gray-500">Profit Factor</span>
                        <span className={`font-semibold ${(strategyData.pf_short ?? 0) >= 1.2 ? "text-emerald-400" : "text-yellow-400"}`}>
                          {(strategyData.pf_short ?? 0).toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center text-gray-600 py-6 text-xs">
                  Aguardando resolução de sinais para métricas LONG/SHORT
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tabela de sinais */}
        <SignalHistoryTable
          signals={signals}
          loading={loading && signals.length === 0}
        />

        {/* Footer */}
        <div className="mt-4 text-center text-xs text-gray-700">
          Phase 6 · Atualiza a cada 60s · Decisões determinísticas e auditáveis
        </div>
      </div>
    </div>
  );
}

function StatBlock({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-gray-800/50 rounded p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  );
}
