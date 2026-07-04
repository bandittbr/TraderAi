"""
Market Structure Engine — Phase 6.5

Orquestrador central da análise de estrutura de mercado.
Integra: Swing Detection + Structure Classification + BOS + SR Zones

Fluxo:
  candles → swings → structure → BOS → SR zones → MarketStructureResult

Resultado é persistido no banco para rastreabilidade e usado pelo Signal Engine V4.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.database import AsyncSessionLocal
from app.services.market_data.store import store as market_store
from app.services.market_structure.swing_detector import (
    get_recent_swings, SwingPoint, SWING_LENGTH_DEFAULT,
)
from app.services.market_structure.structure_classifier import (
    classify_structure, StructureResult, StructureTrend,
)
from app.services.market_structure.bos_detector import (
    detect_bos, BOSResult,
)
from app.services.market_structure.sr_zones import (
    compute_sr_zones, SRAnalysis, SRZone,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Resultado principal
# ─────────────────────────────────────────────

@dataclass
class MarketStructureResult:
    """Resultado completo da análise de estrutura para um (symbol, timeframe)."""
    symbol:     str
    timeframe:  str

    # Tendência estrutural
    trend:          StructureTrend
    confidence:     float           # 0–100%
    structure_label: str            # "HH+HL", "LH+LL", etc.

    # Swing points
    last_swing_high: Optional[float] = None
    last_swing_low:  Optional[float] = None
    prev_swing_high: Optional[float] = None
    prev_swing_low:  Optional[float] = None
    last_high_label: Optional[str]   = None   # "HH" | "LH"
    last_low_label:  Optional[str]   = None   # "HL" | "LL"

    # HH/HL/LH/LL contagens
    hh_count: int = 0
    hl_count: int = 0
    lh_count: int = 0
    ll_count: int = 0

    # BOS
    bos_bullish: bool  = False
    bos_bearish: bool  = False
    bos_level:   Optional[float] = None
    is_choch:    bool  = False
    bos_strength: float = 0.0

    # SR Zones
    nearest_support:    Optional[float] = None
    nearest_resistance: Optional[float] = None
    price_near_support:    bool = False
    price_near_resistance: bool = False
    support_distance_pct:    float = 0.0
    resistance_distance_pct: float = 0.0
    support_zones:    list[dict] = field(default_factory=list)
    resistance_zones: list[dict] = field(default_factory=list)

    # Swing recentes (para exibição no frontend)
    recent_highs: list[dict] = field(default_factory=list)
    recent_lows:  list[dict] = field(default_factory=list)

    # Meta
    candles_analyzed: int = 0
    computed_at: Optional[datetime] = None
    reasons: list[str] = field(default_factory=list)


def _zone_to_dict(z: SRZone) -> dict:
    return {
        "level":       z.level,
        "zone_type":   z.zone_type,
        "touch_count": z.touch_count,
        "strength":    z.strength,
        "range_low":   z.range_low,
        "range_high":  z.range_high,
    }


def _swing_to_dict(s: SwingPoint) -> dict:
    return {
        "index":     s.index,
        "price":     s.price,
        "timestamp": s.timestamp,
        "kind":      s.kind,
    }


# ─────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────

class MarketStructureEngine:
    """
    Singleton que analisa a estrutura de mercado para qualquer (symbol, timeframe).
    Retorna resultado imediato (sem persistência) — a persistência é feita
    pelo scheduler após o cálculo.
    """

    async def analyze(
        self,
        symbol:    str,
        timeframe: str,
        candles:   Optional[list] = None,   # se None, busca do banco
        candle_limit: int = 150,
        swing_length: int = SWING_LENGTH_DEFAULT,
    ) -> MarketStructureResult:
        """
        Analisa a estrutura de mercado para o par (symbol, timeframe).

        Args:
            symbol, timeframe: par de análise
            candles:           candles já carregados (evita re-fetch)
            candle_limit:      quantos candles buscar do banco
            swing_length:      sensibilidade do swing detector

        Returns:
            MarketStructureResult completo.
        """
        # ── 1. Carrega candles ────────────────────────────────────────────────
        if candles is None:
            candles = await market_store.get_candles(symbol, timeframe, limit=candle_limit)

        if len(candles) < swing_length * 2 + 5:
            return MarketStructureResult(
                symbol=symbol, timeframe=timeframe,
                trend=StructureTrend.UNDEFINED, confidence=0.0,
                structure_label="UNDEFINED",
                computed_at=datetime.utcnow(),
                reasons=[f"Candles insuficientes: {len(candles)} (mínimo {swing_length*2+5})"],
            )

        # ── 2. Preço atual ───────────────────────────────────────────────────
        current_price = candles[-1].close

        # ── 3. Detecta swings ────────────────────────────────────────────────
        highs, lows = get_recent_swings(candles, swing_length, max_swings=20)

        # ── 4. Classifica estrutura ──────────────────────────────────────────
        structure: StructureResult = classify_structure(highs, lows)

        # ── 5. Detecta BOS ───────────────────────────────────────────────────
        bos: BOSResult = detect_bos(current_price, highs, lows, structure)

        # ── 6. SR Zones ──────────────────────────────────────────────────────
        sr: SRAnalysis = compute_sr_zones(highs, lows, current_price)

        # ── 7. Monta resultado ───────────────────────────────────────────────
        result = MarketStructureResult(
            symbol     = symbol,
            timeframe  = timeframe,
            trend      = structure.trend,
            confidence = structure.confidence,
            structure_label = structure.structure_label,

            last_swing_high = structure.last_swing_high,
            last_swing_low  = structure.last_swing_low,
            prev_swing_high = structure.prev_swing_high,
            prev_swing_low  = structure.prev_swing_low,
            last_high_label = structure.last_high_label,
            last_low_label  = structure.last_low_label,

            hh_count = structure.hh_count,
            hl_count = structure.hl_count,
            lh_count = structure.lh_count,
            ll_count = structure.ll_count,

            bos_bullish  = bos.bos_bullish,
            bos_bearish  = bos.bos_bearish,
            bos_level    = bos.broke_level,
            is_choch     = bos.is_choch,
            bos_strength = bos.bos_strength,

            nearest_support    = sr.nearest_support.level    if sr.nearest_support    else None,
            nearest_resistance = sr.nearest_resistance.level if sr.nearest_resistance else None,
            price_near_support    = sr.price_near_support,
            price_near_resistance = sr.price_near_resistance,
            support_distance_pct    = sr.support_distance_pct,
            resistance_distance_pct = sr.resistance_distance_pct,
            support_zones    = [_zone_to_dict(z) for z in sr.support_zones],
            resistance_zones = [_zone_to_dict(z) for z in sr.resistance_zones],

            recent_highs = [_swing_to_dict(s) for s in highs[-10:]],
            recent_lows  = [_swing_to_dict(s) for s in lows[-10:]],

            candles_analyzed = len(candles),
            computed_at = datetime.utcnow(),
            reasons = structure.reasons + bos.reasons,
        )

        logger.debug(
            "[structure] %s/%s trend=%s BOS_bull=%s BOS_bear=%s SR_sup=%.2f SR_res=%.2f",
            symbol, timeframe, result.trend.value,
            result.bos_bullish, result.bos_bearish,
            result.nearest_support    or 0,
            result.nearest_resistance or 0,
        )

        return result

    async def save_snapshot(self, result: MarketStructureResult) -> None:
        """Persiste o resultado no banco (market_structure_snapshot)."""
        try:
            from app.models.market_structure import MarketStructureSnapshot
            import json
            async with AsyncSessionLocal() as db:
                snap = MarketStructureSnapshot(
                    symbol          = result.symbol,
                    timeframe       = result.timeframe,
                    trend           = result.trend.value,
                    confidence      = result.confidence,
                    structure_label = result.structure_label,
                    last_swing_high = result.last_swing_high,
                    last_swing_low  = result.last_swing_low,
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
                    nearest_support    = result.nearest_support,
                    nearest_resistance = result.nearest_resistance,
                    price_near_support    = result.price_near_support,
                    price_near_resistance = result.price_near_resistance,
                    support_zones    = json.dumps(result.support_zones),
                    resistance_zones = json.dumps(result.resistance_zones),
                    candles_analyzed = result.candles_analyzed,
                )
                db.add(snap)
                await db.commit()
        except Exception as exc:
            logger.error("[structure] save_snapshot falhou: %s", exc)


# Singleton
market_structure_engine = MarketStructureEngine()
