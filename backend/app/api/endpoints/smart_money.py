"""
API — Smart Money (Phase 7)

Endpoints:
  GET /smc/{symbol}         → análise SMC completa
  GET /smc/{symbol}/sweeps  → apenas sweeps
  GET /smc/{symbol}/fvgs    → apenas FVGs
  GET /smc/{symbol}/volume  → apenas volume profile
"""
from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Query
from app.services.smart_money.engine import smart_money_engine
from app.schemas.smart_money import (
    SmartMoneyResponse, SweepsResponse, FVGsResponse,
    VolumeProfileResponse, SweepEventSchema, FVGSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{symbol}", response_model=SmartMoneyResponse, summary="Análise SMC completa")
async def get_smart_money(
    symbol:    str,
    timeframe: str  = Query("1h"),
    direction: str  = Query("NEUTRAL", description="BUY|SELL|NEUTRAL"),
    save:      bool = Query(False),
):
    symbol = symbol.upper()
    try:
        result = await smart_money_engine.analyze(symbol, timeframe, direction=direction)
    except Exception as exc:
        logger.error("[smc] error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if save:
        await smart_money_engine.save_snapshot(result)

    sweeps_schema = [
        SweepEventSchema(
            sweep_type=s["type"], strength=s["strength"],
            price=s["price"], swept_level=s["swept_level"],
            timestamp=s["timestamp"], penetration_pct=s["penetration_pct"],
            is_stop_hunt=s["is_stop_hunt"],
        ) for s in result.recent_sweeps
    ]
    fvgs_schema = [
        FVGSchema(
            fvg_type=f["type"], status=f["status"],
            gap_top=f["gap_top"], gap_bottom=f["gap_bottom"],
            gap_size_pct=f["gap_size_pct"], distance_pct=f["distance_pct"],
            relevance=f["relevance"], is_filled=f["is_filled"],
        ) for f in result.active_fvgs
    ]

    return SmartMoneyResponse(
        symbol=result.symbol, timeframe=result.timeframe,
        has_recent_buy_sweep=result.has_recent_buy_sweep,
        has_recent_sell_sweep=result.has_recent_sell_sweep,
        sweep_bias=result.sweep_bias,
        last_sweep_type=result.last_sweep_type,
        last_sweep_price=result.last_sweep_price,
        last_sweep_timestamp=result.last_sweep_timestamp,
        recent_sweeps=sweeps_schema,
        has_bullish_fvg=result.has_bullish_fvg,
        has_bearish_fvg=result.has_bearish_fvg,
        bullish_fvg_top=result.bullish_fvg_top,
        bullish_fvg_bottom=result.bullish_fvg_bottom,
        bullish_fvg_distance_pct=result.bullish_fvg_distance_pct,
        bearish_fvg_top=result.bearish_fvg_top,
        bearish_fvg_bottom=result.bearish_fvg_bottom,
        bearish_fvg_distance_pct=result.bearish_fvg_distance_pct,
        active_fvgs=fvgs_schema,
        volume_profile_score=result.volume_profile_score,
        poc=result.poc,
        value_area_high=result.value_area_high,
        value_area_low=result.value_area_low,
        hvn_levels=result.hvn_levels,
        lvn_levels=result.lvn_levels,
        near_hvn=result.near_hvn,
        near_lvn=result.near_lvn,
        price_in_value_area=result.price_in_value_area,
        liquidity_score=result.liquidity_score,
        liquidity_label=result.liquidity_label,
        liq_score_strong=result.liq_score_strong,
        candles_analyzed=result.candles_analyzed,
        computed_at=result.computed_at,
    )


@router.get("/{symbol}/sweeps", response_model=SweepsResponse)
async def get_sweeps(symbol: str, timeframe: str = Query("1h")):
    symbol = symbol.upper()
    try:
        result = await smart_money_engine.analyze(symbol, timeframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    sweeps = [
        SweepEventSchema(
            sweep_type=s["type"], strength=s["strength"],
            price=s["price"], swept_level=s["swept_level"],
            timestamp=s["timestamp"], penetration_pct=s["penetration_pct"],
            is_stop_hunt=s["is_stop_hunt"],
        ) for s in result.recent_sweeps
    ]
    return SweepsResponse(
        symbol=symbol, timeframe=timeframe, events=sweeps,
        buy_count=sum(1 for s in result.recent_sweeps if "BUY" in s["type"]),
        sell_count=sum(1 for s in result.recent_sweeps if "SELL" in s["type"]),
        sweep_bias=result.sweep_bias, computed_at=result.computed_at,
    )


@router.get("/{symbol}/fvgs", response_model=FVGsResponse)
async def get_fvgs(symbol: str, timeframe: str = Query("1h")):
    symbol = symbol.upper()
    try:
        result = await smart_money_engine.analyze(symbol, timeframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    bull = [f for f in result.active_fvgs if f["type"] == "BULLISH"]
    bear = [f for f in result.active_fvgs if f["type"] == "BEARISH"]
    def to_schema(f): return FVGSchema(
        fvg_type=f["type"], status=f["status"],
        gap_top=f["gap_top"], gap_bottom=f["gap_bottom"],
        gap_size_pct=f["gap_size_pct"], distance_pct=f["distance_pct"],
        relevance=f["relevance"], is_filled=f["is_filled"],
    )
    return FVGsResponse(
        symbol=symbol, timeframe=timeframe,
        active_bullish=[to_schema(f) for f in bull],
        active_bearish=[to_schema(f) for f in bear],
        has_bullish_fvg=result.has_bullish_fvg,
        has_bearish_fvg=result.has_bearish_fvg,
        computed_at=result.computed_at,
    )


@router.get("/{symbol}/volume", response_model=VolumeProfileResponse)
async def get_volume_profile(symbol: str, timeframe: str = Query("1h")):
    symbol = symbol.upper()
    try:
        result = await smart_money_engine.analyze(symbol, timeframe)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return VolumeProfileResponse(
        symbol=symbol, timeframe=timeframe,
        volume_profile_score=result.volume_profile_score,
        poc=result.poc, value_area_high=result.value_area_high,
        value_area_low=result.value_area_low,
        hvn_levels=result.hvn_levels, lvn_levels=result.lvn_levels,
        near_hvn=result.near_hvn, near_lvn=result.near_lvn,
        price_in_value_area=result.price_in_value_area,
        computed_at=result.computed_at,
    )
