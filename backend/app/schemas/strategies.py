"""
Fase 11 — Schemas Pydantic para Strategy API.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class StrategyRulesSchema(BaseModel):
    entry_rules: dict[str, Any]
    exit_rules:  dict[str, Any]
    risk_rules:  dict[str, Any]


class StrategyResponse(BaseModel):
    id:               int
    strategy_key:     str
    name:             str
    generation:       int
    origin:           str
    status:           str
    win_rate:         float
    profit_factor:    float
    sharpe:           float
    calmar:           float
    expectancy:       float
    max_drawdown:     float
    n_trades:         int
    strategy_score:   float
    rank_position:    Optional[int] = None
    wf_score:         Optional[float] = None
    mc_ruin_prob:     Optional[float] = None
    stability_score:  Optional[float] = None
    robustness_score: Optional[float] = None
    is_robust:        bool
    rejection_reason: Optional[str] = None
    entry_rules:      dict[str, Any]
    exit_rules:       dict[str, Any]
    risk_rules:       dict[str, Any]
    parent_ids:       list[str]
    created_at:       datetime
    last_evaluated:   Optional[datetime] = None


class StrategyListResponse(BaseModel):
    total:      int
    strategies: list[StrategyResponse]


class BacktestResponse(BaseModel):
    strategy_id:     int
    strategy_key:    str
    symbol:          Optional[str] = None
    period_days:     int
    n_trades:        int
    win_rate:        float
    profit_factor:   float
    sharpe:          float
    calmar:          float
    expectancy:      float
    max_drawdown:    float
    total_return_pct: float
    strategy_score:  float
    executed_at:     datetime


class EvolveResponse(BaseModel):
    status:        str
    n_generated:   int
    n_evaluated:   int
    n_approved:    int
    n_evolved:     int
    top_score:     float
    top_strategy:  Optional[str] = None
    computed_at:   datetime


class RobustnessDetailResponse(BaseModel):
    strategy_id:     int
    wf_score:        float
    wf_is_robust:    bool
    mc_ruin_prob:    float
    mc_dd_p95:       float
    stability_score: float
    n_unstable_cells: int
    robustness_score: float
    approved:        bool
    rejection_reason: Optional[str] = None
    evaluated_at:    datetime
