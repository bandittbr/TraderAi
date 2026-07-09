"""Worker Agent — Pydantic Schemas (V7)."""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class WorkerAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    balance:         float
    initial_balance: float
    peak_balance:    float
    total_pnl:       float
    total_trades:    int
    winning_trades:  int
    losing_trades:   int
    updated_at:      datetime | None = None


class WorkerTradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                    int
    symbol:                str
    timeframe_entry:       str
    trade_side:            str
    entry_price:           float
    exit_price:            float | None
    quantity:              float
    leverage:              int
    stop_loss_price:       float
    take_profit1_price:    float | None
    take_profit2_price:    float | None
    take_profit3_price:    float | None
    break_even_activated:  bool
    trailing_stop_active:  bool
    partial_tp1_hit:       bool
    partial_tp2_hit:       bool
    confidence:            float
    regime_at_entry:       str
    volatility_at_entry:   float
    direction_score:       float
    pnl:                   float | None
    pnl_pct:               float | None
    fee_cost_pct:          float | None
    net_pnl_pct:           float | None
    status:                str
    close_reason:          str | None
    entry_reason:          str | None
    opened_at:             datetime
    closed_at:             datetime | None
    duration_minutes:      float | None


class WorkerRiskOut(BaseModel):
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


class WorkerStatsOut(BaseModel):
    period_days:      int
    total_trades:     int
    open_trades:      int
    win_rate:         float
    profit_factor:    float
    total_pnl_usd:    float
    total_pnl_pct:    float
    avg_trade_pnl:    float
    avg_win_pct:      float
    avg_loss_pct:     float
    max_win_pct:      float
    max_loss_pct:     float
    net_win_rate:     float
    net_profit_factor: float
    total_net_pnl_pct: float
    avg_duration_min: float
    balance:          float
    initial_balance:  float
    peak_balance:     float
    current_leverage: int
    by_symbol:        dict = {}
    by_reason:        dict = {}


class WorkerDebugOut(BaseModel):
    account:        WorkerAccountOut
    open_trades:    list[WorkerTradeOut] = []
    risk_today:     WorkerRiskOut | None = None


class AgentLeaderboardEntry(BaseModel):
    """Um agente no leaderboard do dashboard."""
    name:            str
    status:          str        # "running" | "paused" | "idle"
    win_rate:        float
    profit_factor:   float
    total_pnl_pct:   float
    total_trades:    int
    net_win_rate:    float
    net_profit_factor: float
    total_net_pnl_pct: float
    best:            bool = False


class AgentLeaderboardOut(BaseModel):
    agents: list[AgentLeaderboardEntry]
