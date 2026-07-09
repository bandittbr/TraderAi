/**
 * TradeAI - Cliente HTTP para o Backend (Fase 3)
 * Fase 3: adicionados getAnalysisSummary, getLatestIndicators, getIndicatorsHistory.
 */

import type {
  HealthResponse,
  SystemStatusResponse,
  CandleData,
  MarketStatsResponse,
  PriceResponse,
  SymbolInfo,
  AnalysisSummaryResponse,
  IndicatorData,
} from "@/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: "Erro desconhecido" }));
    throw new Error(error?.detail ?? error?.error ?? `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}

// ── Sistema (Fase 1) ──────────────────────────────────────────────────────────

export async function getHealth(): Promise<HealthResponse | null> {
  try { return await fetchJSON<HealthResponse>("/system/health"); }
  catch { return null; }
}

export async function getSystemStatus(): Promise<SystemStatusResponse | null> {
  try { return await fetchJSON<SystemStatusResponse>("/system/status"); }
  catch { return null; }
}

// ── Mercado (Fase 2) ──────────────────────────────────────────────────────────

export async function getSymbols(): Promise<SymbolInfo[]> {
  try { return await fetchJSON<SymbolInfo[]>("/market/symbols"); }
  catch { return []; }
}

export async function getPrice(symbol: string): Promise<PriceResponse | null> {
  try { return await fetchJSON<PriceResponse>(`/market/price?symbol=${symbol}`); }
  catch { return null; }
}

export async function getMarketStats(symbol: string): Promise<MarketStatsResponse | null> {
  try { return await fetchJSON<MarketStatsResponse>(`/market/stats?symbol=${symbol}`); }
  catch { return null; }
}

export async function getCandles(
  symbol: string,
  timeframe: string,
  limit: number = 100,
): Promise<CandleData[]> {
  try {
    return await fetchJSON<CandleData[]>(
      `/market/candles?symbol=${symbol}&timeframe=${timeframe}&limit=${limit}`,
    );
  } catch { return []; }
}

// ── Indicadores e Análise (Fase 3) ────────────────────────────────────────────

/**
 * Retorna análise técnica completa: indicadores + análise + sinal + score V2.
 * Endpoint: GET /api/v1/analysis/summary
 */
export async function getAnalysisSummary(
  symbol:    string,
  timeframe: string = "1h",
): Promise<AnalysisSummaryResponse | null> {
  try {
    return await fetchJSON<AnalysisSummaryResponse>(
      `/analysis/summary?symbol=${symbol}&timeframe=${timeframe}`,
    );
  } catch { return null; }
}

/**
 * Retorna apenas os valores dos indicadores mais recentes.
 * Endpoint: GET /api/v1/indicators/latest
 */
export async function getLatestIndicators(
  symbol:    string,
  timeframe: string = "1h",
): Promise<IndicatorData | null> {
  try {
    return await fetchJSON<IndicatorData>(
      `/indicators/latest?symbol=${symbol}&timeframe=${timeframe}`,
    );
  } catch { return null; }
}

// ── Paper Trading (Fase 4) ────────────────────────────────────────────────────

import type {
  PaperAccountResponse,
  PaperTradeResponse,
  PaperStatsResponse,
  BacktestResultResponse,
} from "@/types";

export async function getPaperAccount(): Promise<PaperAccountResponse | null> {
  try { return await fetchJSON<PaperAccountResponse>("/paper/account"); }
  catch { return null; }
}

export async function getPaperTrades(
  status: "ALL" | "OPEN" | "CLOSED" = "ALL",
  limit = 100,
): Promise<PaperTradeResponse[]> {
  try {
    return await fetchJSON<PaperTradeResponse[]>(
      `/paper/trades?status=${status}&limit=${limit}`,
    );
  } catch { return []; }
}

export async function getPaperStats(): Promise<PaperStatsResponse | null> {
  try { return await fetchJSON<PaperStatsResponse>("/paper/stats"); }
  catch { return null; }
}

export async function runBacktest(
  symbol: string,
  period_days: number,
): Promise<BacktestResultResponse | null> {
  try {
    return await fetchJSON<BacktestResultResponse>("/backtest/run", {
      method: "POST",
      body: JSON.stringify({ symbol, period_days }),
    });
  } catch { return null; }
}

export async function getBacktestResults(): Promise<BacktestResultResponse[]> {
  try { return await fetchJSON<BacktestResultResponse[]>("/backtest/results"); }
  catch { return []; }
}

// ── Market Context (Fase 5) ───────────────────────────────────────────────────

import type {
  NewsArticle,
  NewsSentimentSummary,
  FearGreedData,
  FundingRateData,
  OpenInterestData,
  ContextScoreData,
} from "@/types";

export async function getNews(
  asset = "ALL", limit = 20, hours = 48,
): Promise<NewsArticle[]> {
  try {
    return await fetchJSON<NewsArticle[]>(
      `/context/news?asset=${asset}&limit=${limit}&hours=${hours}`,
    );
  } catch { return []; }
}

export async function getNewsSentiment(
  asset = "ALL", hours = 24,
): Promise<NewsSentimentSummary | null> {
  try {
    return await fetchJSON<NewsSentimentSummary>(
      `/context/news/sentiment?asset=${asset}&hours=${hours}`,
    );
  } catch { return null; }
}

export async function getFearGreed(): Promise<FearGreedData | null> {
  try { return await fetchJSON<FearGreedData>("/context/fear-greed"); }
  catch { return null; }
}

export async function getFundingRates(): Promise<FundingRateData[]> {
  try { return await fetchJSON<FundingRateData[]>("/context/funding"); }
  catch { return []; }
}

export async function getOpenInterest(): Promise<OpenInterestData[]> {
  try { return await fetchJSON<OpenInterestData[]>("/context/open-interest"); }
  catch { return []; }
}

export async function getContextScore(symbol: string): Promise<ContextScoreData | null> {
  try {
    return await fetchJSON<ContextScoreData>(`/context/score?symbol=${symbol}`);
  } catch { return null; }
}

// ── Analytics — Signal History (Fase 6) ───────────────────────────────────────

import type { SignalHistoryListResponse } from "@/types";

export async function getSignalHistory(
  symbol?: string, period_days = 7, limit = 20,
): Promise<SignalHistoryListResponse | null> {
  try {
    const params = new URLSearchParams({ period_days: String(period_days), limit: String(limit) });
    if (symbol) params.set("symbol", symbol);
    return await fetchJSON<SignalHistoryListResponse>(`/analytics/signals?${params.toString()}`);
  } catch { return null; }
}
