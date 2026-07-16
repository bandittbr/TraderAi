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

export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT" | "STOP_MARKET" | "TAKE_PROFIT_MARKET";
export type OrderStatus = "NEW" | "PARTIALLY_FILLED" | "FILLED" | "CANCELED" | "REJECTED" | "EXPIRED";
export type PositionSide = "LONG" | "SHORT" | "BOTH";
export type BrokerMode = "AUTO" | "MANUAL";

export interface BrokerCredentials {
  api_key: string;
  api_secret: string;
  testnet: boolean;
}

export interface BrokerAccountResponse {
  balances: BrokerBalance[];
  total_usdt: number;
  can_trade: boolean;
  testnet: boolean;
}

export interface BrokerBalance {
  asset: string;
  free: number;
  locked: number;
  total: number;
}

export interface BrokerPosition {
  symbol: string;
  position_side: PositionSide;
  size: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  leverage: number;
  isolated: boolean;
}

export interface BrokerOrderRequest {
  symbol: string;
  side: OrderSide;
  order_type: OrderType;
  quantity: number;
  price?: number;
  stop_price?: number;
  position_side?: PositionSide;
  reduce_only?: boolean;
  client_order_id?: string;
}

export interface BrokerOrderResponse {
  order_id: string;
  client_order_id: string;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  quantity: number;
  price: number;
  status: OrderStatus;
  filled_qty: number;
  avg_price: number;
  commission: number;
  commission_asset: string;
  created_at: string;
  updated_at: string;
}

export interface BrokerConnectRequest {
  api_key: string;
  api_secret: string;
  testnet: boolean;
}

export interface BrokerConnectResponse {
  status: string;
  message: string;
  testnet: boolean;
  balance_usdt: number;
}

export interface BrokerStatusResponse {
  connected: boolean;
  auto_mode: boolean;
  selected_agent: string;
  testnet?: boolean;
  balance_usdt?: number;
}

export interface BrokerAutoModeRequest {
  enabled: boolean;
}

export interface BrokerAgentSelectRequest {
  agent: string;
}

export interface BrokerLeverageRequest {
  symbol: string;
  leverage: number;
}

export interface BrokerMarginTypeRequest {
  symbol: string;
  margin_type: string;
}

// ── Broker mode config ─────────────────────────────────────────────────────────

export interface BrokerModeConfig {
  mode: BrokerMode;
  selected_agent?: string; // "worker" | "scalper" | "paper" | "groq"
}

// ── 10 Multi-Agent Trading System ─────────────────────────────────────────────

export interface AgentInfo {
  name:           string;
  description:    string;
  enabled:        boolean;
  last_execution: string | null;
}

export interface AgentsListResponse {
  agents: AgentInfo[];
}

export interface AgentAccountResponse {
  id:              number;
  agent_name:      string;
  balance:         number;
  initial_balance: number;
  peak_balance:    number;
  total_pnl:       number;
  total_trades:    number;
  winning_trades:  number;
  losing_trades:   number;
  enabled:         boolean;
  updated_at:      string | null;
}

export interface AgentTradeResponse {
  id:                   number;
  agent_name:           string;
  symbol:               string;
  timeframe_entry:      string;
  trade_side:           string;
  entry_price:          number;
  exit_price:           number | null;
  quantity:             number;
  leverage:             number;
  stop_loss_price:      number;
  take_profit_price:    number | null;
  take_profit2_price:   number | null;
  take_profit3_price:   number | null;
  break_even_activated: boolean;
  trailing_stop_active: boolean;
  partial_tp1_hit:      boolean;
  partial_tp2_hit:      boolean;
  confidence:           number;
  regime_at_entry:      string;
  volatility_at_entry:  number;
  pnl:                  number | null;
  pnl_pct:              number | null;
  fee_cost_pct:         number | null;
  net_pnl_pct:          number | null;
  status:               string;
  close_reason:         string | null;
  entry_reason:         string | null;
  opened_at:            string;
  closed_at:            string | null;
  duration_minutes:     number | null;
  unrealized_pnl:       number | null;
  unrealized_pnl_pct:   number | null;
}

export interface AgentStatsResponse {
  agent_name:       string;
  period_days:      number;
  total_trades:     number;
  open_trades:      number;
  win_rate:         number;
  profit_factor:    number;
  total_pnl_usd:    number;
  total_pnl_pct:    number;
  avg_trade_pnl:    number;
  avg_win_pct:      number;
  avg_loss_pct:     number;
  max_win_pct:      number;
  max_loss_pct:     number;
  net_win_rate:     number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  avg_duration_min:  number;
  balance:          number;
  initial_balance:  number;
  peak_balance:     number;
  by_symbol:        Record<string, { trades: number; pnl: number; wins: number }>;
  by_reason:        Record<string, number>;
}

export interface AgentsLeaderboardEntry {
  name:              string;
  status:            string;
  win_rate:          number;
  profit_factor:     number;
  total_pnl_pct:     number;
  total_trades:      number;
  net_win_rate:      number;
  net_profit_factor: number;
  total_net_pnl_pct: number;
  balance:           number;
  best:              boolean;
}

export interface AgentsLeaderboardResponse {
  agents: AgentsLeaderboardEntry[];
}
