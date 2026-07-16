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
  AgentsStatusResponse,
  WorkerAccountResponse,
  ScalperAccountResponse,
  BrokerAccountResponse,
  BrokerPosition,
  BrokerOrderResponse,
  BrokerStatusResponse,
  BrokerModeConfig,
} from "@/types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "";

async function fetchJSON<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_TOKEN) {
    headers["Authorization"] = `Bearer ${API_TOKEN}`;
  }
  const response = await fetch(url, {
    headers,
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

// ── Agent Accounts (Control Center) ───────────────────────────────────────

export async function getAgentsStatus(): Promise<AgentsStatusResponse | null> {
  try { return await fetchJSON<AgentsStatusResponse>("/system/agents-status"); }
  catch { return null; }
}

export async function getWorkerAccount(): Promise<WorkerAccountResponse | null> {
  try { return await fetchJSON<WorkerAccountResponse>("/worker/account"); }
  catch { return null; }
}

export async function getScalperAccount(): Promise<ScalperAccountResponse | null> {
  try { return await fetchJSON<ScalperAccountResponse>("/scalper/account"); }
  catch { return null; }
}

// ── Broker (Binance Real) ──────────────────────────────────────────────────

export async function connectBroker(
  apiKey: string,
  apiSecret: string,
  testnet: boolean = true,
): Promise<{ status: string; message: string; testnet: boolean; balance_usdt: number } | null> {
  try {
    return await fetchJSON("/broker/connect", {
      method: "POST",
      body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret, testnet }),
    });
  } catch { return null; }
}

export async function disconnectBroker(): Promise<{ status: string; message: string } | null> {
  try { return await fetchJSON("/broker/disconnect", { method: "POST" }); }
  catch { return null; }
}

export async function getBrokerStatus(): Promise<BrokerStatusResponse | null> {
  try { return await fetchJSON<BrokerStatusResponse>("/broker/status"); }
  catch { return null; }
}

export async function setBrokerAutoMode(enabled: boolean): Promise<{ status: string; auto_mode: boolean } | null> {
  try { return await fetchJSON("/broker/auto-mode", { method: "POST", body: JSON.stringify({ enabled }) }); }
  catch { return null; }
}

export async function setBrokerAgent(agent: string): Promise<{ status: string; selected_agent: string } | null> {
  try { return await fetchJSON("/broker/select-agent", { method: "POST", body: JSON.stringify({ agent }) }); }
  catch { return null; }
}

export async function getBrokerBalance(): Promise<{ balances: Array<{ asset: string; free: number; locked: number; total: number }> } | null> {
  try { return await fetchJSON("/broker/balance"); }
  catch { return null; }
}

export async function getBrokerPositions(): Promise<{ positions: BrokerPosition[] } | null> {
  try { return await fetchJSON("/broker/positions"); }
  catch { return null; }
}

export async function placeBrokerOrder(order: {
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  price?: number;
  stop_price?: number;
  position_side?: string;
  reduce_only?: boolean;
  client_order_id?: string;
}): Promise<{ status: string; order: BrokerOrderResponse } | null> {
  try { return await fetchJSON("/broker/order", { method: "POST", body: JSON.stringify(order) }); }
  catch { return null; }
}

export async function cancelBrokerOrder(
  symbol: string,
  orderId?: number,
  clientOrderId?: string,
): Promise<{ status: string; result: any } | null> {
  try {
    const params = new URLSearchParams();
    if (orderId) params.append("order_id", String(orderId));
    if (clientOrderId) params.append("client_order_id", clientOrderId);
    return await fetchJSON(`/broker/order/${symbol}?${params}`, { method: "DELETE" });
  } catch { return null; }
}

export async function cancelAllBrokerOrders(symbol: string): Promise<{ status: string; result: any } | null> {
  try { return await fetchJSON(`/broker/orders/${symbol}`, { method: "DELETE" }); }
  catch { return null; }
}

export async function getBrokerOpenOrders(symbol?: string): Promise<{ orders: BrokerOrderResponse[] } | null> {
  try {
    const url = symbol ? `/broker/open-orders?symbol=${symbol}` : "/broker/open-orders";
    return await fetchJSON(url);
  } catch { return null; }
}

export async function setBrokerLeverage(symbol: string, leverage: number): Promise<{ status: string; result: any } | null> {
  try { return await fetchJSON("/broker/leverage", { method: "POST", body: JSON.stringify({ symbol, leverage }) }); }
  catch { return null; }
}

export async function setBrokerMarginType(symbol: string, marginType: string): Promise<{ status: string; result: any } | null> {
  try { return await fetchJSON("/broker/margin-type", { method: "POST", body: JSON.stringify({ symbol, margin_type: marginType }) }); }
  catch { return null; }
}

export async function getBrokerTicker(symbol: string): Promise<any | null> {
  try { return await fetchJSON(`/broker/ticker/${symbol}`); }
  catch { return null; }
}

export async function getBrokerPrice(symbol: string): Promise<{ symbol: string; price: number } | null> {
  try { return await fetchJSON(`/broker/price/${symbol}`); }
  catch { return null; }
}

export async function getBrokerKlines(symbol: string, interval: string = "1h", limit: number = 100): Promise<{ symbol: string; interval: string; klines: any[] } | null> {
  try { return await fetchJSON(`/broker/klines/${symbol}?interval=${interval}&limit=${limit}`); }
  catch { return null; }
}

// ── 10 Multi-Agent Trading System ─────────────────────────────────────────────

import type {
  AgentInfo,
  AgentsListResponse,
  AgentAccountResponse,
  AgentTradeResponse,
  AgentStatsResponse,
  AgentsLeaderboardResponse,
} from "@/types";

export async function getAgentsList(): Promise<AgentsListResponse | null> {
  try { return await fetchJSON<AgentsListResponse>("/agents"); }
  catch { return null; }
}

export async function getAgentInfo(name: string): Promise<AgentInfo | null> {
  try { return await fetchJSON<AgentInfo>(`/agents/${name}`); }
  catch { return null; }
}

export async function getAgentAccount(name: string): Promise<AgentAccountResponse | null> {
  try { return await fetchJSON<AgentAccountResponse>(`/agents/${name}/account`); }
  catch { return null; }
}

export async function getAgentTrades(name: string, status?: string, limit = 50): Promise<AgentTradeResponse[]> {
  try {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    params.append("limit", String(limit));
    return await fetchJSON<AgentTradeResponse[]>(`/agents/${name}/trades?${params}`);
  }
  catch { return []; }
}

export async function getAgentOpenTrades(name: string): Promise<AgentTradeResponse[]> {
  try { return await fetchJSON<AgentTradeResponse[]>(`/agents/${name}/open-trades`); }
  catch { return []; }
}

export async function getAgentStats(name: string, days = 30): Promise<AgentStatsResponse | null> {
  try { return await fetchJSON<AgentStatsResponse>(`/agents/${name}/stats?days=${days}`); }
  catch { return null; }
}

export async function getAgentsLeaderboard(days = 30): Promise<AgentsLeaderboardResponse | null> {
  try { return await fetchJSON<AgentsLeaderboardResponse>(`/agents/leaderboard?days=${days}`); }
  catch { return null; }
}

export async function enableAgent(name: string): Promise<{ status: string; agent: string; enabled: boolean } | null> {
  try { return await fetchJSON(`/agents/${name}/enable`, { method: "POST" }); }
  catch { return null; }
}

export async function disableAgent(name: string): Promise<{ status: string; agent: string; enabled: boolean } | null> {
  try { return await fetchJSON(`/agents/${name}/disable`, { method: "POST" }); }
  catch { return null; }
}
