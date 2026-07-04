"""
TradeAI — Schemas de Trade Management (Fase 12)
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# ── Lifecycle Event ──────────────────────────────────────────────────────────

class TradeLifecycleEvent(BaseModel):
    id:         int
    trade_id:   int
    event_type: str
    price:      Optional[float]
    quantity:   Optional[float]
    pnl:        Optional[float]
    notes:      Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Trade Management Status ───────────────────────────────────────────────────

class TradeManagementStatus(BaseModel):
    trade_id:              int
    symbol:                str
    side:                  str
    entry_price:           float
    current_price:         Optional[float]
    hours_open:            float
    break_even_activated:  bool
    break_even_timestamp:  Optional[datetime]
    trailing_stop_active:  bool
    trailing_stop_price:   Optional[float]
    trailing_stop_peak:    Optional[float]
    tp1_hit:               bool
    tp1_partial_price:     Optional[float]
    tp1_partial_qty:       Optional[float]
    tp1_partial_pnl:       Optional[float]
    remaining_quantity:    Optional[float]
    exit_score:            Optional[float]
    lifecycle:             List[TradeLifecycleEvent]


# ── Trade Management Statistics ──────────────────────────────────────────────

class TradeManagementStats(BaseModel):
    total_closed_trades:      int
    avg_duration_hours:       float
    time_stop_count:          int
    break_even_stop_count:    int
    trailing_stop_count:      int
    stop_loss_count:          int
    take_profit_count:        int
    signal_close_count:       int
    exit_score_count:         int
    partial_tp_count:         int
    time_stop_rate_pct:       float
    trailing_stop_rate_pct:   float
    partial_tp_rate_pct:      float
    avg_exit_score:           Optional[float]
    avg_pnl_time_stop:        Optional[float]
    avg_pnl_trailing_stop:    Optional[float]
    avg_pnl_take_profit:      Optional[float]
    avg_pnl_stop_loss:        Optional[float]


# ── Active Trades with Management Details ────────────────────────────────────

class ActiveTradeDetail(BaseModel):
    id:                    int
    symbol:                str
    side:                  str
    entry_price:           float
    quantity:              float
    opened_at:             datetime
    hours_open:            float
    max_hours:             float
    time_stop_in_hours:    float   # horas restantes para time stop
    break_even_activated:  bool
    trailing_stop_active:  bool
    trailing_stop_price:   Optional[float]
    tp1_hit:               bool
    remaining_quantity:    Optional[float]
    estimated_exit_score:  Optional[float]
    pnl_unrealized:        Optional[float]
    pnl_unrealized_pct:    Optional[float]

    model_config = {"from_attributes": True}
