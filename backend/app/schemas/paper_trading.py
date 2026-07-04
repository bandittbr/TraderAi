"""
TradeAI - Schemas: Paper Trading Futures (LONG + SHORT)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Conta virtual ─────────────────────────────────────────────────────────────

class PaperAccountResponse(BaseModel):
    id:              int
    balance:         float
    initial_balance: float
    pnl_total:       float  = Field(description="balance - initial_balance")
    pnl_pct:         float  = Field(description="((balance / initial_balance) - 1) * 100")
    created_at:      datetime
    updated_at:      datetime

    model_config = {"from_attributes": True}


# ── Trades ────────────────────────────────────────────────────────────────────

class PaperTradeResponse(BaseModel):
    id:           int
    symbol:       str
    timeframe:    str
    signal:       str
    confidence:   float
    trade_side:   str              # "LONG" | "SHORT"
    entry_price:  float
    exit_price:   Optional[float]
    quantity:     float
    pnl:          Optional[float]
    pnl_percent:  Optional[float]
    close_reason: Optional[str]
    status:       str
    opened_at:    datetime
    closed_at:    Optional[datetime]

    model_config = {"from_attributes": True}


# ── Metricas ──────────────────────────────────────────────────────────────────

class PaperStatsResponse(BaseModel):
    total_trades:    int
    open_trades:     int
    closed_trades:   int
    long_trades:     int     = Field(description="Total de trades LONG fechados")
    short_trades:    int     = Field(description="Total de trades SHORT fechados")
    win_rate:        float   = Field(description="% de trades lucrativos")
    win_rate_long:   float   = Field(description="Win rate apenas LONG")
    win_rate_short:  float   = Field(description="Win rate apenas SHORT")
    profit_factor:   float   = Field(description="gross_profit / gross_loss")
    avg_gain:        float   = Field(description="Ganho medio em USD")
    avg_loss:        float   = Field(description="Perda media em USD")
    max_drawdown:    float   = Field(description="Maior queda % do saldo")
    total_pnl:       float
    total_pnl_pct:   float
    current_balance: float


# ── Backtest ──────────────────────────────────────────────────────────────────

class BacktestRequest(BaseModel):
    symbol:      str = Field("BTCUSDT", description="Ex: BTCUSDT, ETHUSDT, SOLUSDT")
    period_days: int = Field(30, description="7 | 30 | 90 | 180")


class BacktestTradeItem(BaseModel):
    symbol:       str
    side:         str   = Field(description="LONG | SHORT")
    entry_price:  float
    exit_price:   float
    entry_time:   Optional[str]
    exit_time:    Optional[str]
    pnl:          float
    pnl_pct:      float
    close_reason: str
    result:       str   # "WIN" | "LOSS"


class BacktestResultResponse(BaseModel):
    symbol:         str
    timeframe:      str
    period_days:    int
    candles_used:   int
    total_trades:   int
    winning_trades: int
    losing_trades:  int
    win_rate:       float

    # Metricas por lado
    long_trades:    int   = 0
    short_trades:   int   = 0
    win_rate_long:  float = 0.0
    win_rate_short: float = 0.0
    pnl_long:       float = 0.0
    pnl_short:      float = 0.0

    # Financeiro
    total_pnl:     float
    total_pnl_pct: float
    avg_gain:      float
    avg_loss:      float
    profit_factor: float
    max_drawdown:  float

    started_at:  datetime
    finished_at: datetime
    trades:      list[BacktestTradeItem] = Field(default_factory=list)
