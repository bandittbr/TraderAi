"""
Phase 6 — Analytics API Endpoints

GET  /analytics/signals          — histórico de sinais recentes
GET  /analytics/signals/{id}     — detalhe de um sinal específico
GET  /analytics/regime/{symbol}  — regime atual e histórico de um ativo
GET  /analytics/metrics          — métricas de performance filtradas
GET  /analytics/strategy         — análise estratégica completa
GET  /analytics/indicators       — ranking de indicadores por WR
POST /analytics/compute          — recalcula e salva snapshot agora
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.analytics import (
    SignalHistory, MarketRegime, StrategyPerformanceSnapshot,
    SignalOutcome, MarketRegimeType,
)
from app.schemas.analytics import (
    SignalHistoryResponse, SignalHistoryListResponse,
    MarketRegimeResponse, RegimeHistoryResponse,
    PerformanceMetricsResponse,
    StrategyAnalyticsResponse, AnalyticsQueryRequest,
    IndicatorWinRate, AssetPerformance, RegimePerformance,
)
from app.services.signal_analytics.strategy_analytics import strategy_analytics
from app.services.signal_analytics.metrics_engine import compute_metrics

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

_CRITERION_LABELS = {
    "rsi_ok":         "RSI zona compra",
    "ema_bull":       "EMA9 > EMA21",
    "ema_macro_bull": "EMA21 > EMA50",
    "ema_price_above":"EMA50 > EMA200",
    "macd_positive":  "MACD positivo",
    "macd_cross":     "Histogram positivo",
    "ema_bear":       "EMA9 < EMA21",
    "ema_macro_bear": "EMA21 < EMA50",
    "ema_price_below":"EMA50 < EMA200",
    "macd_negative":  "MACD negativo",
    "macd_cross_bear":"Histogram negativo",
    "rsi_sell":       "RSI zona venda",
}


# ─────────────────────────────────────────────
# GET /analytics/signals
# ─────────────────────────────────────────────

@router.get("/signals", response_model=SignalHistoryListResponse)
async def get_signal_history(
    symbol:      Optional[str] = Query(None),
    period_days: int           = Query(7, ge=1, le=90),
    limit:       int           = Query(100, ge=1, le=500),
):
    """Retorna histórico recente de sinais emitidos."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    conditions = [SignalHistory.emitted_at >= cutoff]
    if symbol:
        conditions.append(SignalHistory.symbol == symbol)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SignalHistory)
            .where(and_(*conditions))
            .order_by(SignalHistory.emitted_at.desc())
            .limit(limit)
        )
        records = list(result.scalars().all())

    return SignalHistoryListResponse(
        signals     = [SignalHistoryResponse.model_validate(r) for r in records],
        total       = len(records),
        period_days = period_days,
    )


# ─────────────────────────────────────────────
# GET /analytics/signals/{id}
# ─────────────────────────────────────────────

@router.get("/signals/{signal_id}", response_model=SignalHistoryResponse)
async def get_signal_detail(signal_id: int):
    """Retorna detalhe de um sinal específico pelo ID."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SignalHistory).where(SignalHistory.id == signal_id)
        )
        record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(status_code=404, detail="Sinal não encontrado")
    return SignalHistoryResponse.model_validate(record)


# ─────────────────────────────────────────────
# GET /analytics/regime/{symbol}
# ─────────────────────────────────────────────

@router.get("/regime/{symbol}", response_model=RegimeHistoryResponse)
async def get_regime(
    symbol:      str,
    timeframe:   str = Query("1h"),
    history_limit: int = Query(24, ge=1, le=168),
):
    """Regime atual e histórico das últimas N classificações."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MarketRegime)
            .where(
                and_(
                    MarketRegime.symbol    == symbol,
                    MarketRegime.timeframe == timeframe,
                )
            )
            .order_by(MarketRegime.timestamp.desc())
            .limit(history_limit)
        )
        records = list(result.scalars().all())

    current = records[0] if records else None
    return RegimeHistoryResponse(
        symbol    = symbol,
        timeframe = timeframe,
        current   = MarketRegimeResponse.model_validate(current) if current else None,
        history   = [MarketRegimeResponse.model_validate(r) for r in records],
    )


# ─────────────────────────────────────────────
# GET /analytics/metrics
# ─────────────────────────────────────────────

@router.get("/metrics", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    symbol:      Optional[str] = Query(None),
    regime:      Optional[str] = Query(None),
    period_days: int           = Query(30, ge=1, le=365),
):
    """
    Calcula métricas de performance em tempo real sobre signal_history.
    Apenas sinais WIN/LOSS são incluídos.
    """
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=period_days)

    conditions = [
        SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
        SignalHistory.emitted_at >= cutoff,
    ]
    if symbol:
        conditions.append(SignalHistory.symbol == symbol)
    if regime:
        try:
            reg_enum = MarketRegimeType(regime.upper())
            conditions.append(SignalHistory.regime == reg_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Regime inválido: {regime}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SignalHistory).where(and_(*conditions))
        )
        records = list(result.scalars().all())

    resolved = [r for r in records if r.pnl_pct is not None]
    pnls  = [float(r.pnl_pct) for r in resolved]
    durs  = [int(r.trade_duration_min) for r in resolved if r.trade_duration_min is not None]
    sides = [getattr(r, "trade_side", None) or "LONG" for r in resolved]
    m     = compute_metrics(pnls, durs, sides=sides)

    return PerformanceMetricsResponse(
        total_trades           = m.total_trades,
        wins                   = m.wins,
        losses                 = m.losses,
        win_rate               = m.win_rate,
        loss_rate              = m.loss_rate,
        avg_pnl_pct            = m.avg_pnl_pct,
        avg_win_pct            = m.avg_win_pct,
        avg_loss_pct           = m.avg_loss_pct,
        total_pnl_pct          = m.total_pnl_pct,
        profit_factor          = m.profit_factor,
        expectancy             = m.expectancy,
        sharpe_ratio           = m.sharpe_ratio,
        calmar_ratio           = m.calmar_ratio,
        max_drawdown           = m.max_drawdown,
        max_consecutive_wins   = m.max_consecutive_wins,
        max_consecutive_losses = m.max_consecutive_losses,
        avg_duration_min       = m.avg_duration_min,
        median_duration_min    = m.median_duration_min,
        long_trades            = m.long_trades,
        short_trades           = m.short_trades,
        win_rate_long          = m.win_rate_long,
        win_rate_short         = m.win_rate_short,
        pf_long                = m.pf_long,
        pf_short               = m.pf_short,
    )


# ─────────────────────────────────────────────
# GET /analytics/strategy
# ─────────────────────────────────────────────

@router.get("/strategy", response_model=StrategyAnalyticsResponse)
async def get_strategy_analytics(
    symbol:      Optional[str] = Query(None),
    regime:      Optional[str] = Query(None),
    period_days: int           = Query(30, ge=1, le=365),
):
    """Análise estratégica completa com correlação de indicadores."""
    regime_enum: Optional[MarketRegimeType] = None
    if regime:
        try:
            regime_enum = MarketRegimeType(regime.upper())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Regime inválido: {regime}")

    result = await strategy_analytics.analyze(
        symbol      = symbol,
        regime      = regime_enum,
        period_days = period_days,
    )

    # Formatar indicator_win_rates como lista ordenada
    indicator_list = [
        IndicatorWinRate(
            criterion = k,
            win_rate  = v,
            label     = _CRITERION_LABELS.get(k, k),
        )
        for k, v in sorted(
            result.indicator_win_rates.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    # Per-asset como lista ordenada por win_rate
    per_asset_list = [
        AssetPerformance(
            symbol   = sym,
            win_rate = data["win_rate"],
            total    = data["total"],
            avg_pnl  = data["avg_pnl"],
        )
        for sym, data in sorted(
            result.per_asset.items(),
            key=lambda x: x[1]["win_rate"],
            reverse=True,
        )
    ]

    # Per-regime como lista ordenada por win_rate
    per_regime_list = [
        RegimePerformance(
            regime   = reg,
            win_rate = data["win_rate"],
            total    = data["total"],
            avg_pnl  = data["avg_pnl"],
        )
        for reg, data in sorted(
            result.per_regime.items(),
            key=lambda x: x[1]["win_rate"],
            reverse=True,
        )
    ]

    return StrategyAnalyticsResponse(
        symbol             = result.symbol,
        regime             = result.regime.value if result.regime else None,
        period_days        = result.period_days,
        computed_at        = result.computed_at,
        total_signals      = result.total_signals,
        resolved_signals   = result.resolved_signals,
        buy_signals        = result.buy_signals,
        sell_signals       = result.sell_signals,
        wins               = result.wins,
        losses             = result.losses,
        win_rate           = result.win_rate,
        profit_factor      = result.profit_factor,
        expectancy         = result.expectancy,
        sharpe_ratio       = result.sharpe_ratio,
        calmar_ratio       = result.calmar_ratio,
        max_drawdown       = result.max_drawdown,
        avg_pnl_pct        = result.avg_pnl_pct,
        avg_win_pct        = result.avg_win_pct,
        avg_loss_pct       = result.avg_loss_pct,
        avg_duration_min   = result.avg_duration_min,
        long_trades        = result.long_trades,
        short_trades       = result.short_trades,
        win_rate_long      = result.win_rate_long,
        win_rate_short     = result.win_rate_short,
        pf_long            = result.pf_long,
        pf_short           = result.pf_short,
        indicator_win_rates = indicator_list,
        best_combination   = result.best_combination,
        per_asset          = per_asset_list,
        per_regime         = per_regime_list,
    )


# ─────────────────────────────────────────────
# GET /analytics/indicators
# ─────────────────────────────────────────────

@router.get("/indicators", response_model=list[IndicatorWinRate])
async def get_indicator_ranking(
    symbol:      Optional[str] = Query(None),
    period_days: int           = Query(30, ge=1, le=365),
):
    """Ranking dos indicadores por taxa de acerto histórico."""
    result = await strategy_analytics.analyze(
        symbol      = symbol,
        period_days = period_days,
    )
    return [
        IndicatorWinRate(
            criterion = k,
            win_rate  = v,
            label     = _CRITERION_LABELS.get(k, k),
        )
        for k, v in sorted(
            result.indicator_win_rates.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    ]


# ─────────────────────────────────────────────
# POST /analytics/compute
# ─────────────────────────────────────────────

@router.post("/compute", status_code=202)
async def trigger_analytics_compute(req: AnalyticsQueryRequest):
    """
    Dispara recálculo imediato de analytics e salva snapshot no DB.
    Retorna 202 Accepted e processa assincronamente.
    """
    import asyncio

    async def _run():
        from app.models.analytics import MarketRegimeType as MRT
        regime_enum = None
        if req.regime:
            try:
                regime_enum = MRT(req.regime.upper())
            except ValueError as e:
                logger.warning(f"analytics: regime inválido '{req.regime}': {e}", exc_info=True)
        result = await strategy_analytics.analyze(
            symbol      = req.symbol,
            regime      = regime_enum,
            period_days = req.period_days,
        )
        await strategy_analytics.save_snapshot(result)

    asyncio.create_task(_run())
    return {"status": "accepted", "message": "Recálculo agendado em background"}
