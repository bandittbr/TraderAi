"""
Fase 9 — Alpha Discovery Engine Schemas (Pydantic v2)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


# ── Padrão individual ─────────────────────────────────────────────────────────

class PatternStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pattern_key:    str
    criteria:       list[str]
    criteria_count: int
    sample_size:    int
    resolved:       int
    wins:           int
    losses:         int
    win_rate:       float
    profit_factor:  float
    expectancy:     float
    sharpe:         float
    max_drawdown:   float
    avg_win_pct:    float
    avg_loss_pct:   float
    alpha_score:    float
    is_positive:    bool
    sufficient_data: bool
    symbol:         Optional[str] = None
    regime:         Optional[str] = None


# ── Relatório alpha completo ──────────────────────────────────────────────────

class AlphaReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    computed_at:     datetime
    symbol:          Optional[str]
    total_resolved:  int
    baseline_wr:     float
    baseline_pf:     float
    baseline_exp:    float
    best_patterns:   list[PatternStatsResponse]
    worst_patterns:  list[PatternStatsResponse]
    single_criteria: list[PatternStatsResponse]
    combinations:    list[PatternStatsResponse]


# ── Meta-Analytics ────────────────────────────────────────────────────────────

class DimensionStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dimension:      str
    dimension_type: str
    resolved:       int
    wins:           int
    win_rate:       float
    profit_factor:  float
    expectancy:     float
    sharpe:         float
    score:          float


class MetaAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    computed_at:    datetime
    by_symbol:      list[DimensionStatsResponse]
    by_timeframe:   list[DimensionStatsResponse]
    by_regime:      list[DimensionStatsResponse]
    by_context:     list[DimensionStatsResponse]
    by_smc_combo:   list[DimensionStatsResponse]
    by_technical:   list[DimensionStatsResponse]
    best_symbol:    Optional[str]
    best_timeframe: Optional[str]
    best_regime:    Optional[str]
    best_context:   Optional[str]
    best_smc_combo: Optional[str]
    best_technical: Optional[str]
    total_resolved: int
    baseline_wr:    float
    baseline_pf:    float


# ── Setup Quality Score ───────────────────────────────────────────────────────

class SetupQualityRequest(BaseModel):
    symbol:         str
    timeframe:      str                 = "1h"
    signal:         str
    criteria_met:   Optional[list[str]] = None
    regime:         Optional[str]       = None
    context_score:  Optional[float]     = None
    fear_greed:     Optional[float]     = None
    funding_label:  Optional[str]       = None


class SetupQualityResponse(BaseModel):
    symbol:             str
    signal:             str
    quality_score:      float
    pattern_score:      Optional[float] = None
    regime_score:       Optional[float] = None
    context_score_comp: Optional[float] = None
    confluence_score:   Optional[float] = None
    criteria_count:     int             = 0
    computed_at:        datetime


class SetupQualityHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                 int
    symbol:             str
    timeframe:          str
    signal:             Optional[str]
    regime:             Optional[str]
    quality_score:      float
    pattern_score:      Optional[float]
    regime_score:       Optional[float]
    context_score_comp: Optional[float]
    confluence_score:   Optional[float]
    criteria_count:     Optional[int]
    outcome:            Optional[str]
    pnl_pct:            Optional[float]
    computed_at:        datetime


# ── Endpoint de trigger ───────────────────────────────────────────────────────

class AlphaRunResponse(BaseModel):
    success:       bool
    computed_at:   Optional[datetime] = None
    patterns_found: int               = 0
    error:         Optional[str]      = None
