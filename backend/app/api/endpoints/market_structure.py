"""
API — Market Structure (Phase 6.5)

Endpoints:
  GET /structure/{symbol}          → análise completa de estrutura
  GET /structure/{symbol}/zones    → apenas zonas S/R
  GET /structure/{symbol}/swings   → apenas swing points
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.market_structure.engine import market_structure_engine
from app.schemas.market_structure import (
    MarketStructureResponse,
    SRZonesResponse,
    SwingsResponse,
    SRZoneSchema,
    SwingPointSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_sr_zone(d: dict) -> SRZoneSchema:
    return SRZoneSchema(
        level       = d["level"],
        zone_type   = d["zone_type"],
        touch_count = d["touch_count"],
        strength    = d["strength"],
        range_low   = d["range_low"],
        range_high  = d["range_high"],
    )


def _to_swing(d: dict) -> SwingPointSchema:
    return SwingPointSchema(
        index     = d["index"],
        price     = d["price"],
        timestamp = d["timestamp"],
        kind      = d["kind"],
    )


@router.get(
    "/{symbol}",
    response_model=MarketStructureResponse,
    summary="Análise completa de Market Structure",
)
async def get_market_structure(
    symbol:    str,
    timeframe: str = Query("1h", description="Timeframe: 1m, 5m, 15m, 1h, 4h, 1d"),
    save:      bool = Query(False, description="Persistir snapshot no banco"),
):
    """
    Retorna a análise completa de estrutura de mercado para o símbolo/timeframe:
    tendência (HH/HL/LH/LL), BOS/CHoCH, zonas S/R, swing recentes e confidence.
    """
    symbol = symbol.upper()
    try:
        result = await market_structure_engine.analyze(symbol, timeframe)
    except Exception as exc:
        logger.error("[structure] analyze error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if save:
        await market_structure_engine.save_snapshot(result)

    return MarketStructureResponse(
        symbol          = result.symbol,
        timeframe       = result.timeframe,
        trend           = result.trend.value,
        confidence      = result.confidence,
        structure_label = result.structure_label,
        last_swing_high = result.last_swing_high,
        last_swing_low  = result.last_swing_low,
        prev_swing_high = result.prev_swing_high,
        prev_swing_low  = result.prev_swing_low,
        last_high_label = result.last_high_label,
        last_low_label  = result.last_low_label,
        hh_count        = result.hh_count,
        hl_count        = result.hl_count,
        lh_count        = result.lh_count,
        ll_count        = result.ll_count,
        bos_bullish     = result.bos_bullish,
        bos_bearish     = result.bos_bearish,
        bos_level       = result.bos_level,
        is_choch        = result.is_choch,
        bos_strength    = result.bos_strength,
        nearest_support           = result.nearest_support,
        nearest_resistance        = result.nearest_resistance,
        price_near_support        = result.price_near_support,
        price_near_resistance     = result.price_near_resistance,
        support_distance_pct      = result.support_distance_pct,
        resistance_distance_pct   = result.resistance_distance_pct,
        support_zones    = [_to_sr_zone(z) for z in result.support_zones],
        resistance_zones = [_to_sr_zone(z) for z in result.resistance_zones],
        recent_highs     = [_to_swing(s) for s in result.recent_highs],
        recent_lows      = [_to_swing(s) for s in result.recent_lows],
        candles_analyzed = result.candles_analyzed,
        computed_at      = result.computed_at,
        reasons          = result.reasons,
    )


@router.get(
    "/{symbol}/zones",
    response_model=SRZonesResponse,
    summary="Zonas de Suporte e Resistência",
)
async def get_sr_zones(
    symbol:    str,
    timeframe: str = Query("1h"),
):
    """Retorna apenas as zonas de suporte e resistência para o símbolo."""
    symbol = symbol.upper()
    try:
        result = await market_structure_engine.analyze(symbol, timeframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return SRZonesResponse(
        symbol     = result.symbol,
        timeframe  = result.timeframe,
        support_zones    = [_to_sr_zone(z) for z in result.support_zones],
        resistance_zones = [_to_sr_zone(z) for z in result.resistance_zones],
        nearest_support       = result.nearest_support,
        nearest_resistance    = result.nearest_resistance,
        price_near_support    = result.price_near_support,
        price_near_resistance = result.price_near_resistance,
        computed_at           = result.computed_at,
    )


@router.get(
    "/{symbol}/swings",
    response_model=SwingsResponse,
    summary="Swing Highs e Swing Lows recentes",
)
async def get_swings(
    symbol:    str,
    timeframe: str = Query("1h"),
):
    """Retorna os swing points recentes para visualização no frontend."""
    symbol = symbol.upper()
    try:
        result = await market_structure_engine.analyze(symbol, timeframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return SwingsResponse(
        symbol      = result.symbol,
        timeframe   = result.timeframe,
        swing_highs = [_to_swing(s) for s in result.recent_highs],
        swing_lows  = [_to_swing(s) for s in result.recent_lows],
        computed_at = result.computed_at,
    )
