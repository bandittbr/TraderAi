/**
 * TradeAI - Tipos TypeScript Globais (Fase 3)
 * Espelha os schemas Pydantic do backend para garantir consistência de tipos.
 */

// ── Sistema (Fase 1) ──────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database_connected: boolean;
  uptime_seconds: number;
}

export interface SystemStatusResponse {
  backend_status: "online" | "offline";
  database_status: "connected" | "disconnected";
  app_version: string;
  environment: string;
  timestamp: string;
  ai_status: string | null;
  broker_status: string | null;
}

export interface ErrorResponse {
  error: string;
  detail: string | null;
  timestamp: string;
}

// ── UI ────────────────────────────────────────────────────────────────────────

export type StatusLevel = "online" | "offline" | "loading" | "warning";

export interface StatusItem {
  label: string;
  value: string;
  level: StatusLevel;
}

// ── Mercado (Fase 2) ──────────────────────────────────────────────────────────

export interface CandleData {
  time: number;   // epoch seconds
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** Estatísticas 24h + Market Score V2 com breakdown */
export interface MarketStatsResponse {
  symbol:           string;
  price:            number;
  change_24h:       number;
  volume_24h:       number;
  high_24h:         number;
  low_24h:          number;
  market_score:     number;
  trend_score:      number;
  momentum_score:   number;
  volume_score:     number;
  volatility_score: number;
  updated_at:       string;
}

export interface PriceResponse {
  symbol:    string;
  price:     number;
  timestamp: string;
}

export interface SymbolInfo {
  symbol: string;
  name:   string;
  active: boolean;
}

// ── WebSocket (Fase 2) ────────────────────────────────────────────────────────

export interface WsPriceUpdate {
  type:      "price_update";
  symbol:    string;
  price:     number;
  open:      number;
  high:      number;
  low:       number;
  volume:    number;
  timestamp: number;   // epoch ms
}

export type PriceMap = Record<string, WsPriceUpdate>;

// ── Indicadores Técnicos (Fase 3) ─────────────────────────────────────────────

export interface IndicatorData {
  timestamp:      number;
  rsi:            number | null;
  ema_9:          number | null;
  ema_21:         number | null;
  ema_50:         number | null;
  ema_200:        number | null;
  macd:           number | null;
  macd_signal:    number | null;
  macd_histogram: number | null;
  atr:            number | null;
}

export type TrendLabel      = "Strong Bullish" | "Bullish" | "Sideways" | "Bearish" | "Strong Bearish";
export type MomentumLabel   = "Strong" | "Neutral" | "Weak";
export type VolatilityLabel = "Low" | "Medium" | "High";
export type SignalType      = "BUY" | "SELL" | "NEUTRAL";

export interface AnalysisData {
  trend:      TrendLabel;
  momentum:   MomentumLabel;
  volatility: VolatilityLabel;
}

export interface SignalData {
  signal:     SignalType;
  confidence: number;
  reasons:    string[];
}

export interface ScoreBreakdown {
  trend_score:      number;
  momentum_score:   number;
  volume_score:     number;
  volatility_score: number;
  total_score:      number;
}

export interface AnalysisSummaryResponse {
  symbol:     string;
  timeframe:  string;
  indicators: IndicatorData;
  analysis:   AnalysisData;
  signal:     SignalData;
  score:      ScoreBreakdown;
}

// ── Fase 4+: Placeholders ─────────────────────────────────────────────────────

export interface TradingSignal {
  id:         string;
  asset:      string;
  direction:  "BUY" | "SELL" | "HOLD";
  confidence: number;
  timestamp:  string;
}

export interface MarketNews {
  id:        string;
  title:     string;
  source:    string;
  sentiment: "positive" | "negative" | "neutral";
  timestamp: string;
  url:       string;
}

export interface PerformanceStat {
  label:  string;
  value:  number;
  unit:   string;
  change: number;
}

// ── Fase 4: Paper Trading ────────────────────────────────────────────────────

export interface PaperAccountResponse {
  id:              number;
  balance:         number;
  initial_balance: number;
  pnl_total:       number;
  pnl_pct:         number;
  created_at:      string;
  updated_at:      string;
}

export interface PaperTradeResponse {
  id:           number;
  symbol:       string;
  timeframe:    string;
  signal:       string;
  confidence:   number;
  trade_side:   "LONG" | "SHORT";
  entry_price:  number;
  exit_price:   number | null;
  quantity:     number;
  pnl:          number | null;
  pnl_percent:  number | null;
  close_reason: string | null;
  status:       "OPEN" | "CLOSED";
  opened_at:    string;
  closed_at:    string | null;
}

export interface PaperStatsResponse {
  total_trades:    number;
  open_trades:     number;
  closed_trades:   number;
  long_trades:     number;
  short_trades:    number;
  win_rate:        number;
  win_rate_long:   number;
  win_rate_short:  number;
  profit_factor:   number;
  avg_gain:        number;
  avg_loss:        number;
  max_drawdown:    number;
  total_pnl:       number;
  total_pnl_pct:   number;
  current_balance: number;
}

export interface BacktestTradeItem {
  symbol:       string;
  side:         "LONG" | "SHORT";
  entry_price:  number;
  exit_price:   number;
  entry_time:   string | null;
  exit_time:    string | null;
  pnl:          number;
  pnl_pct:      number;
  close_reason: string;
  result:       "WIN" | "LOSS";
}

export interface BacktestResultResponse {
  symbol:         string;
  timeframe:      string;
  period_days:    number;
  candles_used:   number;
  total_trades:   number;
  winning_trades: number;
  losing_trades:  number;
  win_rate:       number;
  long_trades:    number;
  short_trades:   number;
  win_rate_long:  number;
  win_rate_short: number;
  pnl_long:       number;
  pnl_short:      number;
  total_pnl:      number;
  total_pnl_pct:  number;
  avg_gain:       number;
  avg_loss:       number;
  profit_factor:  number;
  max_drawdown:   number;
  started_at:     string;
  finished_at:    string;
  trades:         BacktestTradeItem[];
}

// ── Fase 5: Market Context ────────────────────────────────────────────────────

export interface NewsArticle {
  id:           number;
  source:       string;
  title:        string;
  summary:      string | null;
  url:          string;
  published_at: string;
  asset:        string;
  category:     string;
  sentiment:    "POSITIVE" | "NEUTRAL" | "NEGATIVE";
  impact_score: number;
}

export interface NewsSentimentSummary {
  positive:   number;
  neutral:    number;
  negative:   number;
  total:      number;
  avg_impact: number;
  news_score: number;
}

export interface FearGreedData {
  id:             number;
  value:          number;
  classification: string;
  timestamp:      number;
  created_at:     string;
}

export interface FundingRateData {
  id:           number;
  symbol:       string;
  rate:         number;
  rate_percent: number;
  sentiment:    "BULLISH" | "NEUTRAL" | "BEARISH";
  timestamp:    number;
  created_at:   string;
}

export interface OpenInterestData {
  id:                number;
  symbol:            string;
  open_interest:     number;
  open_interest_usd: number;
  timestamp:         number;
  created_at:        string;
}

export interface ContextScoreData {
  symbol:           string;
  news_score:       number;
  fear_greed:       number;
  fear_greed_label: string;
  funding_score:    number;
  funding_label:    string;
  oi_score:         number;
  oi_change_pct:    number | null;
  context_score:    number;
  context_label:    string;
  news_sentiment:   { positive: number; neutral: number; negative: number; total: number };
}

// ── Agent Accounts (Control Center) ────────────────────────────────────────

export interface AgentStatusEntry {
  name:           string;
  status:         string;  // "online" | "offline" | "idle"
  last_execution: string | null;
  interval_secs:  number | null;
}

export interface AgentsStatusResponse {
  agents: AgentStatusEntry[];
}

export interface WorkerAccountResponse {
  balance:         number;
  initial_balance: number;
  peak_balance:    number;
  total_pnl:       number;
  total_trades:    number;
  winning_trades:  number;
  losing_trades:   number;
  updated_at:      string | null;
}

export interface ScalperAccountResponse {
  balance:         number;
  initial_balance: number;
  peak_balance:    number;
  total_pnl:       number;
  updated_at:      string | null;
}

// ── Groq Agent ─────────────────────────────────────────────────────────────

export interface GroqAccountResponse {
  balance:         number;
  initial_balance: number;
  peak_balance:    number;
  total_pnl:       number;
  total_trades:    number;
  winning_trades:  number;
  losing_trades:   number;
}

export interface GroqStatsResponse {
  period_days:       number;
  total_trades:      number;
  open_trades:       number;
  win_rate:          number;
  profit_factor:     number;
  total_pnl_usd:     number;
  total_pnl_pct:     number;
  net_win_rate:      number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  avg_duration_min:  number;
  balance:           number;
  initial_balance:   number;
  peak_balance:      number;
  avg_win_pct:       number;
  avg_loss_pct:      number;
  max_win_pct:       number;
  max_loss_pct:      number;
}

export interface GroqTradeResponse {
  id:             number;
  symbol:         string;
  side:           string;
  entry_price:    number;
  exit_price:     number | null;
  quantity:       number;
  stop_loss:      number;
  take_profit:    number;
  pnl:            number | null;
  pnl_pct:        number | null;
  net_pnl_pct:    number | null;
  status:         string;
  close_reason:   string | null;
  confidence:     number | null;
  regime:         string | null;
  opened_at:      string;
  closed_at:      string | null;
  duration_minutes: number | null;
}

export interface GroqThinkingResponse {
  id:             number;
  symbol:         string;
  action:         string;
  confidence:     number | null;
  reasoning:      string;
  model:          string;
  latency_ms:     number | null;
  prompt_tokens:  number | null;
  output_tokens:  number | null;
  error:          string | null;
  created_at:     string;
}

export interface GroqDebugResponse {
  signals_processed: number;
  last_execution:    string | null;
  consecutive_losses: number;
  is_paused:         boolean;
  sizing_factor:     number;
  model:             string;
  frequency:         string;
}
