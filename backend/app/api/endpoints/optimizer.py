"""
Fase 8 — Optimizer API Endpoints

GET /optimizer/summary          — ciclo completo de otimização (cache 5min)
GET /optimizer/criteria         — performance por critério
GET /optimizer/combinations     — top combinações
GET /optimizer/regime           — performance por regime
GET /optimizer/weights          — pesos atuais
GET /optimizer/backtest-compare — V5 vs V6
GET /optimizer/snapshot         — último snapshot salvo
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.optimizer import (
    CriterionPerformanceResponse,
    CriterionStatsResponse,
    CombinationReportResponse,
    CombinationStatsResponse,
    RegimeReportResponse,
    RegimeDataResponse,
    RegimeCriterionStatsResponse,
    WeightSnapshotResponse,
    OptimizationSummaryResponse,
    BacktestComparisonResponse,
    LatestSnapshotResponse,
)
from app.services.optimizer.criterion_performance import criterion_performance_engine
from app.services.optimizer.combination_analyzer import combination_analyzer
from app.services.optimizer.regime_performance import regime_performance_analyzer
from app.services.optimizer.weight_engine import weight_engine
from app.services.optimizer.optimizer_engine import optimizer_engine
from app.services.optimizer.backtest_compare import backtest_compare_engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary", response_model=OptimizationSummaryResponse)
async def get_optimizer_summary(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
):
    """Ciclo completo: criterion perf + combinations + regime + weight update."""
    result = await optimizer_engine.run(symbol=symbol, lookback_days=lookback_days)
    cr     = result.criterion_report
    cb     = result.combination_report
    reg    = result.regime_report

    # Regime summary compacto
    regime_summary = {}
    for name, rd in reg.regimes.items():
        regime_summary[name] = {
            "n": rd.total_signals,
            "baseline_wr": rd.baseline_wr,
            "baseline_pf": rd.baseline_pf,
            "best": rd.best_criteria,
            "avoid": rd.avoid_criteria,
        }

    top_combos = [
        CombinationStatsResponse(
            criteria=list(c.criteria), criteria_key=c.criteria_key,
            sample_size=c.sample_size, wins=c.wins, losses=c.losses,
            win_rate=c.win_rate, profit_factor=c.profit_factor,
            expectancy=c.expectancy, sharpe=c.sharpe,
            max_drawdown=c.max_drawdown, score=c.score,
        )
        for c in cb.top_all[:20]
    ]

    return OptimizationSummaryResponse(
        symbol=symbol,
        total_resolved=cr.total_resolved,
        baseline_wr=cr.baseline_wr,
        baseline_pf=cr.baseline_pf,
        baseline_exp=cr.baseline_exp,
        top_criteria=cr.top_criteria,
        worst_criteria=cr.worst_criteria,
        weights=result.weight_snapshot.weights,
        top_combinations=top_combos,
        regime_summary=regime_summary,
        computed_at=result.computed_at,
        snapshot_id=result.snapshot_id,
    )


@router.get("/criteria", response_model=CriterionPerformanceResponse)
async def get_criteria_performance(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
):
    report = await criterion_performance_engine.compute(symbol, lookback_days)
    return CriterionPerformanceResponse(
        criteria=[
            CriterionStatsResponse(**{
                "criterion": s.criterion, "sample_size": s.sample_size,
                "resolved": s.resolved, "wins": s.wins, "losses": s.losses,
                "win_rate": s.win_rate, "profit_factor": s.profit_factor,
                "expectancy": s.expectancy, "sharpe": s.sharpe,
                "max_drawdown": s.max_drawdown, "avg_win_pct": s.avg_win_pct,
                "avg_loss_pct": s.avg_loss_pct, "sufficient_data": s.sufficient_data,
            })
            for s in report.criteria
        ],
        baseline_wr=report.baseline_wr,
        baseline_pf=report.baseline_pf,
        baseline_exp=report.baseline_exp,
        total_resolved=report.total_resolved,
        top_criteria=report.top_criteria,
        worst_criteria=report.worst_criteria,
    )


@router.get("/combinations", response_model=CombinationReportResponse)
async def get_combinations(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
    top_n:         int           = Query(50, ge=5, le=200),
):
    report = await combination_analyzer.compute(symbol, lookback_days, top_n)
    return CombinationReportResponse(
        top_all=[
            CombinationStatsResponse(
                criteria=list(c.criteria), criteria_key=c.criteria_key,
                sample_size=c.sample_size, wins=c.wins, losses=c.losses,
                win_rate=c.win_rate, profit_factor=c.profit_factor,
                expectancy=c.expectancy, sharpe=c.sharpe,
                max_drawdown=c.max_drawdown, score=c.score,
            )
            for c in report.top_all
        ],
        analyzed=report.analyzed,
        valid=report.valid,
    )


@router.get("/regime", response_model=RegimeReportResponse)
async def get_regime_performance(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
):
    report = await regime_performance_analyzer.compute(symbol, lookback_days)
    regimes_out = {}
    for name, rd in report.regimes.items():
        regimes_out[name] = RegimeDataResponse(
            regime=rd.regime,
            total_signals=rd.total_signals,
            baseline_wr=rd.baseline_wr,
            baseline_pf=rd.baseline_pf,
            best_criteria=rd.best_criteria,
            avoid_criteria=rd.avoid_criteria,
            criteria_stats=[
                RegimeCriterionStatsResponse(
                    criterion=s.criterion, regime=s.regime,
                    sample_size=s.sample_size, win_rate=s.win_rate,
                    profit_factor=s.profit_factor, expectancy=s.expectancy,
                    recommended=s.recommended, avoid=s.avoid,
                )
                for s in rd.criteria_stats
            ],
        )
    return RegimeReportResponse(regimes=regimes_out, total_rows=report.total_rows)


@router.get("/weights", response_model=WeightSnapshotResponse)
async def get_current_weights():
    snap = await weight_engine.get_current_snapshot()
    return WeightSnapshotResponse(weights=snap.weights, computed_at=snap.computed_at)


@router.get("/backtest-compare", response_model=BacktestComparisonResponse)
async def get_backtest_comparison(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
):
    return await backtest_compare_engine.compare(symbol=symbol, lookback_days=lookback_days)


@router.get("/snapshot", response_model=Optional[LatestSnapshotResponse])
async def get_latest_snapshot():
    snap = await optimizer_engine.get_latest_snapshot()
    if snap is None:
        return None
    top_combos = json.loads(snap.top_combos_json or "[]")
    weights    = json.loads(snap.weights_json or "{}")
    top_crit   = json.loads(snap.top_criteria_json or "[]")
    worst_crit = json.loads(snap.worst_criteria_json or "[]")
    regime_sum = json.loads(snap.regime_json or "{}")
    return LatestSnapshotResponse(
        id=snap.id,
        symbol=snap.symbol,
        total_resolved=snap.total_resolved or 0,
        baseline_wr=snap.baseline_wr,
        baseline_pf=snap.baseline_pf,
        top_criteria=top_crit,
        worst_criteria=worst_crit,
        top_combinations=top_combos,
        weights=weights,
        regime_summary=regime_sum,
        computed_at=snap.computed_at,
    )
