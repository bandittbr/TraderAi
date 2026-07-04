"""
Fase 8 — Optimizer Schemas (Pydantic V2)
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CriterionStatsResponse(BaseModel):
    criterion:      str
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
    sufficient_data: bool


class CriterionPerformanceResponse(BaseModel):
    criteria:       list[CriterionStatsResponse]
    baseline_wr:    float
    baseline_pf:    float
    baseline_exp:   float
    total_resolved: int
    top_criteria:   list[str]
    worst_criteria: list[str]


class CombinationStatsResponse(BaseModel):
    criteria:       list[str]
    criteria_key:   str
    sample_size:    int
    wins:           int
    losses:         int
    win_rate:       float
    profit_factor:  float
    expectancy:     float
    sharpe:         float
    max_drawdown:   float
    score:          float


class CombinationReportResponse(BaseModel):
    top_all:  list[CombinationStatsResponse]
    analyzed: int
    valid:    int


class RegimeCriterionStatsResponse(BaseModel):
    criterion:     str
    regime:        str
    sample_size:   int
    win_rate:      float
    profit_factor: float
    expectancy:    float
    recommended:   bool
    avoid:         bool


class RegimeDataResponse(BaseModel):
    regime:         str
    total_signals:  int
    baseline_wr:    float
    baseline_pf:    float
    best_criteria:  list[str]
    avoid_criteria: list[str]
    criteria_stats: list[RegimeCriterionStatsResponse]


class RegimeReportResponse(BaseModel):
    regimes:    dict[str, RegimeDataResponse]
    total_rows: int


class WeightSnapshotResponse(BaseModel):
    weights:     dict[str, float]   # {criterion: weight}
    computed_at: Optional[datetime]


class OptimizationSummaryResponse(BaseModel):
    """Resposta principal do endpoint GET /optimizer/summary"""
    symbol:            Optional[str]
    total_resolved:    int
    baseline_wr:       float
    baseline_pf:       float
    baseline_exp:      float
    top_criteria:      list[str]
    worst_criteria:    list[str]
    weights:           dict[str, float]
    top_combinations:  list[CombinationStatsResponse]
    regime_summary:    dict[str, dict]   # {regime: {best, avoid, n}}
    computed_at:       Optional[datetime]
    snapshot_id:       Optional[int]


class BacktestComparisonResponse(BaseModel):
    """Comparativo V5 vs V6"""
    symbol:         Optional[str]
    lookback_days:  int
    v5_win_rate:    Optional[float]
    v5_profit_factor: Optional[float]
    v5_sharpe:      Optional[float]
    v5_drawdown:    Optional[float]
    v5_expectancy:  Optional[float]
    v5_signals:     int
    v6_win_rate:    Optional[float]
    v6_profit_factor: Optional[float]
    v6_sharpe:      Optional[float]
    v6_drawdown:    Optional[float]
    v6_expectancy:  Optional[float]
    v6_signals:     int
    improvement_wr:    Optional[float]   # v6 - v5
    improvement_pf:    Optional[float]
    computed_at:    datetime


class LatestSnapshotResponse(BaseModel):
    """Snapshot mais recente do banco."""
    id:             int
    symbol:         Optional[str]
    total_resolved: int
    baseline_wr:    Optional[float]
    baseline_pf:    Optional[float]
    top_criteria:   list[str]
    worst_criteria: list[str]
    top_combinations: list[dict]
    weights:        dict[str, float]
    regime_summary: dict
    computed_at:    datetime
