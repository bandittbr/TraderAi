"""
Multi-Agent Trading System — Pydantic Schemas
"""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AgentInfo(BaseModel):
    """Informação de um agente registrado."""
    name:            str
    description:     str
    enabled:         bool
    last_execution:  str | None = None


class AgentAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:              int
    agent_name:      str
    balance:         float
    initial_balance: float
    peak_balance:    float
    total_pnl:       float
    total_trades:    int
    winning_trades:  int
    losing_trades:   int
    enabled:         bool
    updated_at:      datetime | None = None


class AgentTradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id:                    int
    agent_name:            str
    symbol:                str
    timeframe_entry:       str
    trade_side:            str
    entry_price:           float
    exit_price:            float | None
    quantity:              float
    leverage:              int
    stop_loss_price:       float
    take_profit_price:     float | None
    take_profit2_price:    float | None
    take_profit3_price:    float | None
    break_even_activated:  bool
    trailing_stop_active:  bool
    partial_tp1_hit:       bool
    partial_tp2_hit:       bool
    confidence:            float
    regime_at_entry:       str
    volatility_at_entry:   float
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
    # Unrealized P&L for open trades
    unrealized_pnl:        float | None = None
    unrealized_pnl_pct:    float | None = None


class AgentStatsOut(BaseModel):
    """Estatísticas de um agente."""
    agent_name:       str
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
    avg_duration_min:  float
    balance:          float
    initial_balance:  float
    peak_balance:     float
    by_symbol:        dict = {}
    by_reason:        dict = {}


class AgentsListOut(BaseModel):
    """Lista de agentes registrados."""
    agents: list[AgentInfo]


class AgentsLeaderboardEntry(BaseModel):
    """Um agente no leaderboard."""
    name:            str
    status:          str        # "running" | "paused" | "idle"
    win_rate:        float
    profit_factor:   float
    total_pnl_pct:   float
    total_trades:    int
    net_win_rate:    float
    net_profit_factor: float
    total_net_pnl_pct: float
    balance:         float = 0.0
    best:            bool = False


class AgentsLeaderboardOut(BaseModel):
    agents: list[AgentsLeaderboardEntry]
