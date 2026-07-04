"""
Fase 10 — Endpoints da Robustness API
4 rotas: walk-forward, monte-carlo, stability, report (+ run)
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.robustness import (
    WalkForwardResponse,
    MonteCarloResponse,
    StabilityResponse,
    RobustnessReportResponse,
    RobustnessRunResponse,
    PhaseMetricsSchema,
    DimensionCellSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── helpers de conversão ──────────────────────────────────────────────────────

def _phase_schema(pm) -> Optional[PhaseMetricsSchema]:
    if pm is None:
        return None
    return PhaseMetricsSchema(
        phase         = pm.phase,
        n_trades      = pm.n_trades,
        win_rate      = pm.win_rate,
        profit_factor = pm.profit_factor,
        sharpe        = pm.sharpe,
        expectancy    = pm.expectancy,
        max_drawdown  = pm.max_drawdown,
        sufficient    = pm.sufficient,
    )


def _cell_schema(c) -> DimensionCellSchema:
    return DimensionCellSchema(
        dimension_type  = c.dimension_type,
        dimension_value = c.dimension_value,
        n_trades        = c.n_trades,
        win_rate        = c.win_rate,
        profit_factor   = c.profit_factor,
        expectancy      = c.expectancy,
        baseline_wr     = c.baseline_wr,
        baseline_pf     = c.baseline_pf,
        wr_vs_baseline  = c.wr_vs_baseline,
        pf_vs_baseline  = c.pf_vs_baseline,
        stability_score = c.stability_score,
        is_unstable     = c.is_unstable,
        unstable_reason = c.unstable_reason,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/walk-forward", response_model=WalkForwardResponse)
async def get_walk_forward(
    symbol:      Optional[str] = Query(None),
    pattern_key: Optional[str] = Query(None),
    train_days:  int           = Query(60, ge=10, le=365),
    val_days:    int           = Query(30, ge=5,  le=180),
    test_days:   int           = Query(30, ge=5,  le=180),
):
    """Valida estratégia via Walk Forward (treino/validação/teste)."""
    from app.services.robustness.walk_forward import walk_forward_validator
    report = await walk_forward_validator.validate(
        symbol=symbol, pattern_key=pattern_key,
        train_days=train_days, val_days=val_days, test_days=test_days,
        persist=False,
    )
    return WalkForwardResponse(
        symbol          = report.symbol,
        pattern_key     = report.pattern_key,
        train_days      = report.train_days,
        val_days        = report.val_days,
        test_days       = report.test_days,
        n_trades_total  = report.n_trades_total,
        train           = _phase_schema(report.train),
        validation      = _phase_schema(report.validation),
        test            = _phase_schema(report.test),
        wr_degradation  = report.wr_degradation,
        pf_degradation  = report.pf_degradation,
        dd_increase     = report.dd_increase,
        wf_score        = report.wf_score,
        is_robust       = report.is_robust,
        computed_at     = report.computed_at,
    )


@router.get("/monte-carlo", response_model=MonteCarloResponse)
async def get_monte_carlo(
    symbol:         Optional[str] = Query(None),
    pattern_key:    Optional[str] = Query(None),
    n_simulations:  int           = Query(5000, ge=100, le=20000),
    ruin_threshold: float         = Query(20.0, ge=5.0, le=50.0),
):
    """Executa N simulações Monte Carlo sobre a sequência de trades."""
    from app.services.robustness.monte_carlo import monte_carlo_engine
    report = await monte_carlo_engine.simulate(
        symbol=symbol, pattern_key=pattern_key,
        n_simulations=n_simulations, ruin_threshold=ruin_threshold,
        persist=False,
    )
    return MonteCarloResponse(
        symbol           = report.symbol,
        pattern_key      = report.pattern_key,
        n_simulations    = report.n_simulations,
        n_trades         = report.n_trades,
        dd_median        = report.dd_median,
        dd_p95           = report.dd_p95,
        dd_p99           = report.dd_p99,
        dd_max_observed  = report.dd_max_observed,
        ret_median       = report.ret_median,
        ret_p5           = report.ret_p5,
        ret_p95          = report.ret_p95,
        ruin_threshold   = report.ruin_threshold,
        ruin_probability = report.ruin_probability,
        expected_wr      = report.expected_wr,
        wr_std           = report.wr_std,
        dd_histogram     = report.dd_histogram,
        computed_at      = report.computed_at,
    )


@router.get("/stability", response_model=StabilityResponse)
async def get_stability(
    symbol:      Optional[str] = Query(None),
    pattern_key: Optional[str] = Query(None),
    lookback_days: int         = Query(90, ge=7, le=365),
):
    """Analisa estabilidade da estratégia por dimensão (ativo/regime/timeframe/período)."""
    from app.services.robustness.stability import strategy_stability_analyzer
    report = await strategy_stability_analyzer.analyze(
        symbol=symbol, pattern_key=pattern_key,
        lookback_days=lookback_days, persist=False,
    )
    return StabilityResponse(
        symbol                  = report.symbol,
        pattern_key             = report.pattern_key,
        n_total_trades          = report.n_total_trades,
        baseline_wr             = report.baseline_wr,
        baseline_pf             = report.baseline_pf,
        by_symbol               = [_cell_schema(c) for c in report.by_symbol],
        by_regime               = [_cell_schema(c) for c in report.by_regime],
        by_timeframe            = [_cell_schema(c) for c in report.by_timeframe],
        by_period               = [_cell_schema(c) for c in report.by_period],
        overall_stability_score = report.overall_stability_score,
        n_unstable_cells        = report.n_unstable_cells,
        computed_at             = report.computed_at,
    )


@router.get("/report", response_model=RobustnessReportResponse)
async def get_robustness_report(
    symbol:      Optional[str] = Query(None),
    pattern_key: Optional[str] = Query(None),
):
    """Relatório consolidado: Walk Forward + Monte Carlo + Stability + Score global."""
    from app.services.robustness.robustness_engine import robustness_engine
    report = await robustness_engine.run(
        symbol=symbol, pattern_key=pattern_key, persist=False,
    )

    def _wf_resp(wf):
        if wf is None:
            return None
        return WalkForwardResponse(
            symbol=wf.symbol, pattern_key=wf.pattern_key,
            train_days=wf.train_days, val_days=wf.val_days, test_days=wf.test_days,
            n_trades_total=wf.n_trades_total,
            train=_phase_schema(wf.train),
            validation=_phase_schema(wf.validation),
            test=_phase_schema(wf.test),
            wr_degradation=wf.wr_degradation, pf_degradation=wf.pf_degradation,
            dd_increase=wf.dd_increase, wf_score=wf.wf_score, is_robust=wf.is_robust,
            computed_at=wf.computed_at,
        )

    def _mc_resp(mc):
        if mc is None:
            return None
        return MonteCarloResponse(
            symbol=mc.symbol, pattern_key=mc.pattern_key,
            n_simulations=mc.n_simulations, n_trades=mc.n_trades,
            dd_median=mc.dd_median, dd_p95=mc.dd_p95, dd_p99=mc.dd_p99,
            dd_max_observed=mc.dd_max_observed,
            ret_median=mc.ret_median, ret_p5=mc.ret_p5, ret_p95=mc.ret_p95,
            ruin_threshold=mc.ruin_threshold, ruin_probability=mc.ruin_probability,
            expected_wr=mc.expected_wr, wr_std=mc.wr_std,
            dd_histogram=mc.dd_histogram, computed_at=mc.computed_at,
        )

    def _st_resp(st):
        if st is None:
            return None
        return StabilityResponse(
            symbol=st.symbol, pattern_key=st.pattern_key,
            n_total_trades=st.n_total_trades,
            baseline_wr=st.baseline_wr, baseline_pf=st.baseline_pf,
            by_symbol=[_cell_schema(c) for c in st.by_symbol],
            by_regime=[_cell_schema(c) for c in st.by_regime],
            by_timeframe=[_cell_schema(c) for c in st.by_timeframe],
            by_period=[_cell_schema(c) for c in st.by_period],
            overall_stability_score=st.overall_stability_score,
            n_unstable_cells=st.n_unstable_cells,
            computed_at=st.computed_at,
        )

    return RobustnessReportResponse(
        symbol           = report.symbol,
        pattern_key      = report.pattern_key,
        walk_forward     = _wf_resp(report.walk_forward),
        monte_carlo      = _mc_resp(report.monte_carlo),
        stability        = _st_resp(report.stability),
        robustness_score = report.robustness_score,
        interpretation   = report.interpretation,
        computed_at      = report.computed_at,
    )


@router.post("/run", response_model=RobustnessRunResponse)
async def run_robustness(
    symbol:        Optional[str] = Query(None),
    pattern_key:   Optional[str] = Query(None),
    n_simulations: int           = Query(5000, ge=100, le=20000),
):
    """Executa e persiste análise completa de robustez (com persistência no banco)."""
    from app.services.robustness.robustness_engine import robustness_engine
    report = await robustness_engine.run(
        symbol=symbol, pattern_key=pattern_key,
        n_simulations=n_simulations, persist=True,
    )
    return RobustnessRunResponse(
        status           = "ok",
        symbol           = report.symbol,
        pattern_key      = report.pattern_key,
        robustness_score = report.robustness_score,
        interpretation   = report.interpretation,
        computed_at      = report.computed_at,
    )
