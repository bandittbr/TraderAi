"""Scalper Engine — Pydantic Schemas (Fase 13)."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ScalperAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    balance:         float
    initial_balance: float
    peak_balance:    float
    total_pnl:       float
    updated_at:      datetime | None = None


class ScalperTradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                    int
    symbol:                str
    timeframe_entry:       str
    trade_side:            str
    trend_15m:             str
    confidence:            float
    entry_price:           float
    exit_price:            float | None
    quantity:              float
    stop_loss_price:       float
    take_profit_price:     float
    break_even_activated:  bool
    trailing_stop_active:  bool
    trailing_stop_price:   float | None
    pnl:                   float | None
    pnl_pct:               float | None
    status:                str
    close_reason:          str | None
    opened_at:             datetime
    closed_at:             datetime | None
    duration_minutes:      float | None


class ScalperRiskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                  int
    date:                str
    daily_pnl_usd:       float
    daily_pnl_pct:       float
    consecutive_losses:  int
    total_trades:        int
    winning_trades:      int
    losing_trades:       int
    is_blocked:          bool
    block_reason:        str | None


class ScalperSignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:            int
    symbol:        str
    direction:     str
    trend_15m:     str
    confirm_5m:    bool
    entry_1m:      bool
    confidence:    float
    price:         float
    rsi_1m:        float | None
    rsi_5m:        float | None
    ema9_15m:      float | None
    ema21_15m:     float | None
    acted_on:      bool
    reject_reason: str | None
    emitted_at:    datetime


class ScalperStatsOut(BaseModel):
    period_days:       int
    total_trades:      int
    open_trades:       int
    win_rate:          float
    profit_factor:     float
    total_pnl_usd:     float
    total_pnl_pct:     float
    avg_trade_pnl:     float
    avg_win_pct:       float
    avg_loss_pct:      float
    max_win_pct:       float
    max_loss_pct:      float
    avg_duration_min:  float
    balance:           float
    initial_balance:   float
    peak_balance:      float
    by_side:           dict
    by_symbol:         dict
    by_reason:         dict


class ScalperDebugOut(BaseModel):
    signals_processed:   int
    last_execution:      str | None
    balance:             float
    total_pnl:           float
    peak_balance:        float
    risk_blocked:        bool
    consecutive_losses:  int
    daily_pnl_pct:       float
