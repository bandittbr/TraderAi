"""
Fase 10 — Schemas Pydantic para Robustness API.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Walk Forward ──────────────────────────────────────────────────────────────

class PhaseMetricsSchema(BaseModel):
    phase:          str
    n_trades:       int
    win_rate:       float
    profit_factor:  float
    sharpe:         float
    expectancy:     float
    max_drawdown:   float
    sufficient:     bool


class WalkForwardResponse(BaseModel):
    symbol:          Optional[str]      = None
    pattern_key:     Optional[str]      = None
    train_days:      int
    val_days:        int
    test_days:       int
    n_trades_total:  int
    train:           Optional[PhaseMetricsSchema] = None
    validation:      Optional[PhaseMetricsSchema] = None
    test:            Optional[PhaseMetricsSchema] = None
    wr_degradation:  float
    pf_degradation:  float
    dd_increase:     float
    wf_score:        float
    is_robust:       bool
    computed_at:     datetime


# ── Monte Carlo ───────────────────────────────────────────────────────────────

class MonteCarloResponse(BaseModel):
    symbol:          Optional[str]  = None
    pattern_key:     Optional[str]  = None
    n_simulations:   int
    n_trades:        int
    dd_median:       float
    dd_p95:          float
    dd_p99:          float
    dd_max_observed: float
    ret_median:      float
    ret_p5:          float
    ret_p95:         float
    ruin_threshold:  float
    ruin_probability: float
    expected_wr:     float
    wr_std:          float
    dd_histogram:    dict
    computed_at:     datetime


# ── Stability ─────────────────────────────────────────────────────────────────

class DimensionCellSchema(BaseModel):
    dimension_type:  str
    dimension_value: str
    n_trades:        int
    win_rate:        float
    profit_factor:   float
    expectancy:      float
    baseline_wr:     float
    baseline_pf:     float
    wr_vs_baseline:  float
    pf_vs_baseline:  float
    stability_score: float
    is_unstable:     bool
    unstable_reason: Optional[str] = None


class StabilityResponse(BaseModel):
    symbol:                Optional[str]             = None
    pattern_key:           Optional[str]             = None
    n_total_trades:        int
    baseline_wr:           float
    baseline_pf:           float
    by_symbol:             list[DimensionCellSchema]
    by_regime:             list[DimensionCellSchema]
    by_timeframe:          list[DimensionCellSchema]
    by_period:             list[DimensionCellSchema]
    overall_stability_score: float
    n_unstable_cells:      int
    computed_at:           datetime


# ── Robustness Report ─────────────────────────────────────────────────────────

class RobustnessReportResponse(BaseModel):
    symbol:           Optional[str]              = None
    pattern_key:      Optional[str]              = None
    walk_forward:     Optional[WalkForwardResponse]  = None
    monte_carlo:      Optional[MonteCarloResponse]   = None
    stability:        Optional[StabilityResponse]    = None
    robustness_score: float
    interpretation:   str
    computed_at:      datetime


# ── Run request ───────────────────────────────────────────────────────────────

class RobustnessRunResponse(BaseModel):
    status:           str
    symbol:           Optional[str]   = None
    pattern_key:      Optional[str]   = None
    robustness_score: float
    interpretation:   str
    computed_at:      datetime
