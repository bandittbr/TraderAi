"""
Schemas Pydantic v2 — Phase 6 Analytics
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Signal History
# ─────────────────────────────────────────────

class SignalHistoryResponse(BaseModel):
    id:                 int
    symbol:             str
    timeframe:          str
    signal:             str
    confidence:         float
    regime:             str
    rsi:                Optional[float]
    ema_alignment:      Optional[str]
    macd_histogram:     Optional[float]
    atr:                Optional[float]
    price_at_emission:  Optional[float]
    criteria_met:       Optional[str]          # JSON string
    criteria_count:     Optional[int]
    context_boost:      int
    news_sentiment:     Optional[str]
    fear_greed_value:   Optional[float]
    context_score:      Optional[float]
    outcome:            str
    entry_price:        Optional[float]
    exit_price:         Optional[float]
    pnl_pct:            Optional[float]
    max_favorable_pct:  Optional[float]
    max_adverse_pct:    Optional[float]
    trade_duration_min: Optional[int]
    exit_reason:        Optional[str]
    emitted_at:         datetime
    resolved_at:        Optional[datetime]

    model_config = {"from_attributes": True}


class SignalHistoryListResponse(BaseModel):
    signals:     list[SignalHistoryResponse]
    total:       int
    period_days: int


# ─────────────────────────────────────────────
# Market Regime
# ─────────────────────────────────────────────

class MarketRegimeResponse(BaseModel):
    id:                  int
    symbol:              str
    timeframe:           str
    regime:              str
    confidence:          float
    ema_alignment_score: Optional[float]
    atr_pct:             Optional[float]
    price_vs_ema200_pct: Optional[float]
    ema9_vs_ema21_pct:   Optional[float]
    rsi:                 Optional[float]
    timestamp:           datetime

    model_config = {"from_attributes": True}


class RegimeHistoryResponse(BaseModel):
    symbol:   str
    timeframe: str
    current:  Optional[MarketRegimeResponse]
    history:  list[MarketRegimeResponse]


# ─────────────────────────────────────────────
# Performance Metrics
# ─────────────────────────────────────────────

class PerformanceMetricsResponse(BaseModel):
    total_trades:            int
    wins:                    int
    losses:                  int
    win_rate:                float     # %
    loss_rate:               float     # %
    avg_pnl_pct:             float
    avg_win_pct:             float
    avg_loss_pct:            float
    total_pnl_pct:           float
    profit_factor:           float
    expectancy:              float     # % por trade
    sharpe_ratio:            float
    calmar_ratio:            float
    max_drawdown:            float     # negativo
    max_consecutive_wins:    int
    max_consecutive_losses:  int
    avg_duration_min:        float
    median_duration_min:     float
    # LONG vs SHORT
    long_trades:             int   = 0
    short_trades:            int   = 0
    win_rate_long:           float = 0.0
    win_rate_short:          float = 0.0
    pf_long:                 float = 0.0
    pf_short:                float = 0.0


# ─────────────────────────────────────────────
# Strategy Analytics
# ─────────────────────────────────────────────

class IndicatorWinRate(BaseModel):
    criterion:  str
    win_rate:   float     # %
    label:      str       # nome amigável


class AssetPerformance(BaseModel):
    symbol:   str
    win_rate: float
    total:    int
    avg_pnl:  float


class RegimePerformance(BaseModel):
    regime:   str
    win_rate: float
    total:    int
    avg_pnl:  float


class StrategyAnalyticsResponse(BaseModel):
    symbol:              Optional[str]
    regime:              Optional[str]
    period_days:         int
    computed_at:         datetime

    # Contagens
    total_signals:       int
    resolved_signals:    int
    buy_signals:         int
    sell_signals:        int
    wins:                int
    losses:              int

    # Métricas principais
    win_rate:            float
    profit_factor:       float
    expectancy:          float
    sharpe_ratio:        float
    calmar_ratio:        float
    max_drawdown:        float
    avg_pnl_pct:         float
    avg_win_pct:         float
    avg_loss_pct:        float
    avg_duration_min:    float

    # LONG vs SHORT
    long_trades:         int   = 0
    short_trades:        int   = 0
    win_rate_long:       float = 0.0
    win_rate_short:      float = 0.0
    pf_long:             float = 0.0
    pf_short:            float = 0.0

    # Análise de indicadores
    indicator_win_rates: list[IndicatorWinRate]
    best_combination:    list[str]

    # Rankings
    per_asset:           list[AssetPerformance]
    per_regime:          list[RegimePerformance]


# ─────────────────────────────────────────────
# Requests
# ─────────────────────────────────────────────

class AnalyticsQueryRequest(BaseModel):
    symbol:      Optional[str] = None
    regime:      Optional[str] = None
    period_days: int           = Field(default=30, ge=1, le=365)
