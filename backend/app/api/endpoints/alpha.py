"""
Fase 9 — Alpha Discovery Engine API Endpoints
Rotas: /api/v1/alpha/*
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.alpha import (
    AlphaReportResponse,
    AlphaRunResponse,
    MetaAnalyticsResponse,
    PatternStatsResponse,
    SetupQualityRequest,
    SetupQualityResponse,
    SetupQualityHistoryResponse,
    DimensionStatsResponse,
)
from app.services.alpha.alpha_engine import alpha_engine
from app.services.alpha.pattern_engine import alpha_pattern_engine
from app.services.alpha.meta_analytics import meta_analytics_engine
from app.services.alpha.quality_scorer import setup_quality_scorer

logger  = logging.getLogger(__name__)
router  = APIRouter()


# ── GET /alpha/patterns ───────────────────────────────────────────────────────

@router.get("/patterns", response_model=AlphaReportResponse)
async def get_alpha_patterns(
    symbol:        Optional[str] = Query(None, description="Filtrar por ativo"),
    lookback_days: int           = Query(90, ge=7, le=365),
    run_fresh:     bool          = Query(False, description="Forçar recálculo imediato"),
):
    """
    Retorna padrões identificados no histórico de sinais.
    Inclui padrões positivos, negativos e combinações.
    """
    try:
        if run_fresh:
            result = await alpha_engine.run(symbol=symbol, lookback_days=lookback_days)
            if result.pattern_report:
                return _map_alpha_report(result.pattern_report)

        # Usar cache ou calcular
        report = await alpha_pattern_engine.compute(
            symbol=symbol, lookback_days=lookback_days, persist=False
        )
        return _map_alpha_report(report)
    except Exception as exc:
        logger.error("[alpha] /patterns: %s", exc)
        return AlphaReportResponse(
            computed_at=datetime.utcnow(), symbol=symbol,
            total_resolved=0, baseline_wr=0, baseline_pf=0, baseline_exp=0,
            best_patterns=[], worst_patterns=[], single_criteria=[], combinations=[],
        )


# ── GET /alpha/best-setups ────────────────────────────────────────────────────

@router.get("/best-setups", response_model=list[PatternStatsResponse])
async def get_best_setups(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
    limit:         int           = Query(20, ge=1, le=50),
):
    """Top N padrões que geram maior alpha positivo."""
    try:
        report = await alpha_pattern_engine.compute(
            symbol=symbol, lookback_days=lookback_days, persist=False
        )
        patterns = report.best_patterns[:limit]
        return [_map_pattern(p) for p in patterns]
    except Exception as exc:
        logger.error("[alpha] /best-setups: %s", exc)
        return []


# ── GET /alpha/worst-setups ───────────────────────────────────────────────────

@router.get("/worst-setups", response_model=list[PatternStatsResponse])
async def get_worst_setups(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
    limit:         int           = Query(10, ge=1, le=30),
):
    """Top N padrões que geram maior prejuízo — fatores de risco."""
    try:
        report = await alpha_pattern_engine.compute(
            symbol=symbol, lookback_days=lookback_days, persist=False
        )
        patterns = report.worst_patterns[:limit]
        return [_map_pattern(p) for p in patterns]
    except Exception as exc:
        logger.error("[alpha] /worst-setups: %s", exc)
        return []


# ── GET /alpha/quality ────────────────────────────────────────────────────────

@router.get("/quality", response_model=list[SetupQualityHistoryResponse])
async def get_quality_history(
    symbol: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=200),
):
    """Histórico de quality scores calculados para sinais recentes."""
    try:
        entries = await setup_quality_scorer.get_latest(symbol=symbol, limit=limit)
        return [SetupQualityHistoryResponse.model_validate(e) for e in entries]
    except Exception as exc:
        logger.error("[alpha] /quality: %s", exc)
        return []


# ── POST /alpha/quality/score ─────────────────────────────────────────────────

@router.post("/quality/score", response_model=SetupQualityResponse)
async def compute_quality_score(payload: SetupQualityRequest):
    """Calcula o Setup Quality Score para um sinal em tempo real."""
    try:
        # Calcular componentes separados para auditoria
        criteria  = payload.criteria_met or []
        n_crit    = len(criteria)

        from app.services.alpha.quality_scorer import (
            _confluence_score, REGIME_BASE_SCORE
        )
        confluence = _confluence_score(n_crit)
        regime_sc  = REGIME_BASE_SCORE.get(str(payload.regime or "").upper(), 10.0)

        # Pattern score (async)
        from app.services.alpha.quality_scorer import SetupQualityScorer
        scorer = SetupQualityScorer()
        pattern_sc = await scorer._pattern_score(criteria, payload.signal)
        ctx_sc     = scorer._context_component(
            payload.context_score, payload.fear_greed,
            payload.funding_label, payload.signal
        )
        total = min(100.0, round(pattern_sc + regime_sc + ctx_sc + confluence, 2))

        return SetupQualityResponse(
            symbol              = payload.symbol,
            signal              = payload.signal,
            quality_score       = total,
            pattern_score       = pattern_sc,
            regime_score        = regime_sc,
            context_score_comp  = ctx_sc,
            confluence_score    = confluence,
            criteria_count      = n_crit,
            computed_at         = datetime.utcnow(),
        )
    except Exception as exc:
        logger.error("[alpha] /quality/score: %s", exc)
        return SetupQualityResponse(
            symbol=payload.symbol, signal=payload.signal,
            quality_score=0.0, computed_at=datetime.utcnow(),
        )


# ── GET /alpha/report ─────────────────────────────────────────────────────────

@router.get("/report", response_model=MetaAnalyticsResponse)
async def get_alpha_report(
    lookback_days: int = Query(90, ge=7, le=365),
):
    """
    Relatório meta-analytics: melhores ativo, timeframe, regime,
    contexto, combinação SMC e combinação técnica.
    """
    try:
        report = await meta_analytics_engine.compute(lookback_days=lookback_days)
        return MetaAnalyticsResponse(
            computed_at    = report.computed_at,
            by_symbol      = [_map_dim(d) for d in report.by_symbol],
            by_timeframe   = [_map_dim(d) for d in report.by_timeframe],
            by_regime      = [_map_dim(d) for d in report.by_regime],
            by_context     = [_map_dim(d) for d in report.by_context],
            by_smc_combo   = [_map_dim(d) for d in report.by_smc_combo],
            by_technical   = [_map_dim(d) for d in report.by_technical],
            best_symbol    = report.best_symbol,
            best_timeframe = report.best_timeframe,
            best_regime    = report.best_regime,
            best_context   = report.best_context,
            best_smc_combo = report.best_smc_combo,
            best_technical = report.best_technical,
            total_resolved = report.total_resolved,
            baseline_wr    = report.baseline_wr,
            baseline_pf    = report.baseline_pf,
        )
    except Exception as exc:
        logger.error("[alpha] /report: %s", exc)
        return MetaAnalyticsResponse(
            computed_at=datetime.utcnow(),
            by_symbol=[], by_timeframe=[], by_regime=[], by_context=[],
            by_smc_combo=[], by_technical=[],
            best_symbol=None, best_timeframe=None, best_regime=None,
            best_context=None, best_smc_combo=None, best_technical=None,
            total_resolved=0, baseline_wr=0, baseline_pf=0,
        )


# ── POST /alpha/run ───────────────────────────────────────────────────────────

@router.post("/run", response_model=AlphaRunResponse)
async def run_alpha_cycle(
    symbol:        Optional[str] = Query(None),
    lookback_days: int           = Query(90, ge=7, le=365),
):
    """Dispara manualmente um ciclo completo de análise alpha."""
    result = await alpha_engine.run(symbol=symbol, lookback_days=lookback_days)
    n_patterns = 0
    if result.pattern_report:
        n_patterns = len(result.pattern_report.best_patterns) + len(result.pattern_report.worst_patterns)
    return AlphaRunResponse(
        success        = result.success,
        computed_at    = result.computed_at,
        patterns_found = n_patterns,
        error          = result.error,
    )


# ── Mappers ───────────────────────────────────────────────────────────────────

def _map_pattern(p) -> PatternStatsResponse:
    return PatternStatsResponse(
        pattern_key    = p.pattern_key,
        criteria       = p.criteria,
        criteria_count = p.criteria_count,
        sample_size    = p.sample_size,
        resolved       = p.resolved,
        wins           = p.wins,
        losses         = p.losses,
        win_rate       = p.win_rate,
        profit_factor  = p.profit_factor,
        expectancy     = p.expectancy,
        sharpe         = p.sharpe,
        max_drawdown   = p.max_drawdown,
        avg_win_pct    = p.avg_win_pct,
        avg_loss_pct   = p.avg_loss_pct,
        alpha_score    = p.alpha_score,
        is_positive    = p.is_positive,
        sufficient_data = p.sufficient_data,
        symbol         = getattr(p, "symbol", None),
        regime         = getattr(p, "regime", None),
    )


def _map_alpha_report(report) -> AlphaReportResponse:
    return AlphaReportResponse(
        computed_at     = report.computed_at,
        symbol          = report.symbol,
        total_resolved  = report.total_resolved,
        baseline_wr     = report.baseline_wr,
        baseline_pf     = report.baseline_pf,
        baseline_exp    = report.baseline_exp,
        best_patterns   = [_map_pattern(p) for p in report.best_patterns],
        worst_patterns  = [_map_pattern(p) for p in report.worst_patterns],
        single_criteria = [_map_pattern(p) for p in report.single_criteria],
        combinations    = [_map_pattern(p) for p in report.combinations],
    )


def _map_dim(d) -> DimensionStatsResponse:
    return DimensionStatsResponse(
        dimension      = d.dimension,
        dimension_type = d.dimension_type,
        resolved       = d.resolved,
        wins           = d.wins,
        win_rate       = d.win_rate,
        profit_factor  = d.profit_factor,
        expectancy     = d.expectancy,
        sharpe         = d.sharpe,
        score          = d.score,
    )
