"""
Smart Money Engine — Phase 7

Orquestrador que integra:
  - Liquidity Sweep Detector
  - Fair Value Gap Engine
  - Volume Profile Lite
  - Liquidity Score

Produz SmartMoneyResult completo para um (symbol, timeframe).
Persiste snapshot via save_snapshot().
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from app.database import AsyncSessionLocal
from app.services.market_data.store import store as market_store
from app.services.smart_money.liquidity_sweep import detect_sweeps, SweepAnalysis, SweepEvent
from app.services.smart_money.fvg_engine      import detect_fvgs,  FVGAnalysis, FVGEvent
from app.services.smart_money.volume_profile  import compute_volume_profile, VolumeProfile
from app.services.smart_money.liquidity_score import compute_liquidity_score, LiquidityScoreResult

logger = logging.getLogger(__name__)


# ── Resultado principal ────────────────────────────────────────────────────────

@dataclass
class SmartMoneyResult:
    symbol:    str
    timeframe: str

    # Sweeps
    has_recent_buy_sweep:  bool = False
    has_recent_sell_sweep: bool = False
    sweep_bias:            str  = "NEUTRAL"
    last_sweep_type:       Optional[str] = None
    last_sweep_price:      Optional[float] = None
    last_sweep_timestamp:  Optional[int] = None
    recent_sweeps:         List[dict] = field(default_factory=list)

    # FVG
    has_bullish_fvg:         bool  = False
    has_bearish_fvg:         bool  = False
    bullish_fvg_top:         Optional[float] = None
    bullish_fvg_bottom:      Optional[float] = None
    bullish_fvg_distance_pct: float = 0.0
    bearish_fvg_top:         Optional[float] = None
    bearish_fvg_bottom:      Optional[float] = None
    bearish_fvg_distance_pct: float = 0.0
    active_fvgs:             List[dict] = field(default_factory=list)

    # Volume Profile
    volume_profile_score: float = 50.0
    poc:                  Optional[float] = None
    value_area_high:      Optional[float] = None
    value_area_low:       Optional[float] = None
    hvn_levels:           List[float] = field(default_factory=list)
    lvn_levels:           List[float] = field(default_factory=list)
    near_hvn:             bool = False
    near_lvn:             bool = False
    price_in_value_area:  bool = False

    # Liquidity Score (calculado depois que o sinal é determinado)
    liquidity_score:      float = 50.0
    liquidity_label:      str   = "Neutral"
    liq_score_strong:     bool  = False

    # Meta
    candles_analyzed: int = 0
    computed_at: Optional[datetime] = None

    # Objetos internos (não serializados no ORM)
    _sweep_analysis: Optional[SweepAnalysis] = field(default=None, repr=False, compare=False)
    _fvg_analysis:   Optional[FVGAnalysis]   = field(default=None, repr=False, compare=False)
    _volume_profile: Optional[VolumeProfile] = field(default=None, repr=False, compare=False)


def _sweep_to_dict(e: SweepEvent) -> dict:
    return {
        "type":           e.sweep_type.value,
        "strength":       e.strength.value,
        "price":          e.price,
        "swept_level":    e.swept_level,
        "timestamp":      e.timestamp,
        "penetration_pct": e.penetration_pct,
        "is_stop_hunt":   e.is_stop_hunt,
    }


def _fvg_to_dict(f: FVGEvent) -> dict:
    return {
        "type":         f.fvg_type.value,
        "status":       f.status.value,
        "gap_top":      f.gap_top,
        "gap_bottom":   f.gap_bottom,
        "gap_size_pct": f.gap_size_pct,
        "distance_pct": f.distance_pct,
        "relevance":    f.relevance_score,
        "is_filled":    f.is_filled,
    }


# ── Engine ─────────────────────────────────────────────────────────────────────

class SmartMoneyEngine:
    """Singleton que computa o quadro completo de Smart Money para (symbol, tf)."""

    async def analyze(
        self,
        symbol:    str,
        timeframe: str,
        candles:   Optional[list] = None,
        candle_limit: int = 150,
        structure  = None,   # MarketStructureResult opcional (Phase 6.5)
        direction: str = "NEUTRAL",
    ) -> SmartMoneyResult:

        # ── 1. Candles ─────────────────────────────────────────────────────────
        if candles is None:
            candles = await market_store.get_candles(symbol, timeframe, limit=candle_limit)

        if len(candles) < 15:
            return SmartMoneyResult(
                symbol=symbol, timeframe=timeframe,
                computed_at=datetime.utcnow(),
            )

        current_price = candles[-1].close

        # ── 2. Sweeps ──────────────────────────────────────────────────────────
        sweep_result = detect_sweeps(candles)

        # ── 3. FVGs ────────────────────────────────────────────────────────────
        fvg_result = detect_fvgs(candles, current_price)

        # ── 4. Volume Profile ──────────────────────────────────────────────────
        vp_result = compute_volume_profile(candles, current_price)

        # ── 5. Liquidity Score (para direção solicitada) ───────────────────────
        liq_score = compute_liquidity_score(
            direction      = direction,
            sweep_analysis = sweep_result,
            fvg_analysis   = fvg_result,
            volume_profile = vp_result,
            structure      = structure,
        )

        # ── 6. Montar resultado ────────────────────────────────────────────────
        last_bs = sweep_result.recent_buy_sweep
        last_ss = sweep_result.recent_sell_sweep
        last_any = (
            last_bs if (last_bs and (not last_ss or last_bs.candle_index > last_ss.candle_index))
            else last_ss
        )

        nb = fvg_result.nearest_bullish
        nbear = fvg_result.nearest_bearish
        all_fvgs = (
            list(fvg_result.active_bullish[:3]) +
            list(fvg_result.active_bearish[:3])
        )

        result = SmartMoneyResult(
            symbol    = symbol,
            timeframe = timeframe,

            has_recent_buy_sweep  = sweep_result.has_recent_buy_sweep,
            has_recent_sell_sweep = sweep_result.has_recent_sell_sweep,
            sweep_bias            = sweep_result.sweep_bias,
            last_sweep_type       = last_any.sweep_type.value    if last_any else None,
            last_sweep_price      = last_any.price               if last_any else None,
            last_sweep_timestamp  = last_any.timestamp           if last_any else None,
            recent_sweeps         = [_sweep_to_dict(e) for e in sweep_result.events[-5:]],

            has_bullish_fvg         = fvg_result.has_bullish_fvg,
            has_bearish_fvg         = fvg_result.has_bearish_fvg,
            bullish_fvg_top         = nb.gap_top    if nb else None,
            bullish_fvg_bottom      = nb.gap_bottom if nb else None,
            bullish_fvg_distance_pct = fvg_result.bullish_fvg_distance_pct,
            bearish_fvg_top         = nbear.gap_top    if nbear else None,
            bearish_fvg_bottom      = nbear.gap_bottom if nbear else None,
            bearish_fvg_distance_pct = fvg_result.bearish_fvg_distance_pct,
            active_fvgs             = [_fvg_to_dict(f) for f in all_fvgs],

            volume_profile_score = vp_result.volume_profile_score,
            poc                  = vp_result.point_of_control,
            value_area_high      = vp_result.value_area_high,
            value_area_low       = vp_result.value_area_low,
            hvn_levels           = vp_result.hvn_levels,
            lvn_levels           = vp_result.lvn_levels,
            near_hvn             = vp_result.near_hvn,
            near_lvn             = vp_result.near_lvn,
            price_in_value_area  = vp_result.price_in_value_area,

            liquidity_score  = liq_score.score,
            liquidity_label  = liq_score.label.value,
            liq_score_strong = liq_score.is_strong,

            candles_analyzed = len(candles),
            computed_at      = datetime.utcnow(),

            _sweep_analysis = sweep_result,
            _fvg_analysis   = fvg_result,
            _volume_profile = vp_result,
        )

        logger.debug(
            "[smc] %s/%s sweeps=%d fvgs=%d vp=%.0f liq=%.0f(%s)",
            symbol, timeframe,
            len(sweep_result.events), len(fvg_result.all_fvgs),
            vp_result.volume_profile_score,
            liq_score.score, liq_score.label.value,
        )
        return result

    async def save_snapshot(self, result: SmartMoneyResult) -> None:
        """Persiste o resultado no banco."""
        try:
            from app.models.smart_money import SmartMoneySnapshot
            import json
            async with AsyncSessionLocal() as db:
                snap = SmartMoneySnapshot(
                    symbol                = result.symbol,
                    timeframe             = result.timeframe,
                    computed_at           = result.computed_at,
                    has_recent_buy_sweep  = result.has_recent_buy_sweep,
                    has_recent_sell_sweep = result.has_recent_sell_sweep,
                    sweep_bias            = result.sweep_bias,
                    last_sweep_type       = result.last_sweep_type,
                    last_sweep_price      = result.last_sweep_price,
                    has_bullish_fvg       = result.has_bullish_fvg,
                    has_bearish_fvg       = result.has_bearish_fvg,
                    bullish_fvg_top       = result.bullish_fvg_top,
                    bullish_fvg_bottom    = result.bullish_fvg_bottom,
                    bearish_fvg_top       = result.bearish_fvg_top,
                    bearish_fvg_bottom    = result.bearish_fvg_bottom,
                    volume_profile_score  = result.volume_profile_score,
                    poc                   = result.poc,
                    value_area_high       = result.value_area_high,
                    value_area_low        = result.value_area_low,
                    hvn_levels            = json.dumps(result.hvn_levels),
                    lvn_levels            = json.dumps(result.lvn_levels),
                    near_hvn              = result.near_hvn,
                    near_lvn              = result.near_lvn,
                    liquidity_score       = result.liquidity_score,
                    liquidity_label       = result.liquidity_label,
                    candles_analyzed      = result.candles_analyzed,
                )
                db.add(snap)
                await db.commit()
        except Exception as exc:
            logger.error("[smc] save_snapshot falhou: %s", exc)


# Singleton
smart_money_engine = SmartMoneyEngine()
