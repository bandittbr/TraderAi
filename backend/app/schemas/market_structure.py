"""
Pydantic v2 — Schemas para Market Structure (Phase 6.5)
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── Zona SR ───────────────────────────────────────────────────────────────────

class SRZoneSchema(BaseModel):
    level:       float
    zone_type:   Literal["SUPPORT", "RESISTANCE"]
    touch_count: int
    strength:    Literal["WEAK", "MODERATE", "STRONG"]
    range_low:   float
    range_high:  float


# ── Swing Point ───────────────────────────────────────────────────────────────

class SwingPointSchema(BaseModel):
    index:     int
    price:     float
    timestamp: int
    kind:      Literal["HIGH", "LOW"]


# ── Resposta principal ────────────────────────────────────────────────────────

class MarketStructureResponse(BaseModel):
    symbol:     str
    timeframe:  str

    # Estrutura
    trend:           str
    confidence:      float = Field(ge=0, le=100)
    structure_label: str

    # Swings
    last_swing_high: Optional[float] = None
    last_swing_low:  Optional[float] = None
    prev_swing_high: Optional[float] = None
    prev_swing_low:  Optional[float] = None
    last_high_label: Optional[str]   = None
    last_low_label:  Optional[str]   = None

    hh_count: int = 0
    hl_count: int = 0
    lh_count: int = 0
    ll_count: int = 0

    # BOS
    bos_bullish:  bool  = False
    bos_bearish:  bool  = False
    bos_level:    Optional[float] = None
    is_choch:     bool  = False
    bos_strength: float = 0.0

    # SR
    nearest_support:          Optional[float] = None
    nearest_resistance:       Optional[float] = None
    price_near_support:       bool  = False
    price_near_resistance:    bool  = False
    support_distance_pct:     float = 0.0
    resistance_distance_pct:  float = 0.0
    support_zones:    List[SRZoneSchema]    = []
    resistance_zones: List[SRZoneSchema]   = []

    # Swings recentes para visualização
    recent_highs: List[SwingPointSchema] = []
    recent_lows:  List[SwingPointSchema] = []

    # Meta
    candles_analyzed: int = 0
    computed_at:      Optional[datetime] = None
    reasons:          List[str] = []


# ── Resposta de zones ─────────────────────────────────────────────────────────

class SRZonesResponse(BaseModel):
    symbol:     str
    timeframe:  str
    support_zones:    List[SRZoneSchema]  = []
    resistance_zones: List[SRZoneSchema] = []
    nearest_support:       Optional[float] = None
    nearest_resistance:    Optional[float] = None
    price_near_support:    bool  = False
    price_near_resistance: bool  = False
    computed_at:           Optional[datetime] = None


# ── Resposta de swings ────────────────────────────────────────────────────────

class SwingsResponse(BaseModel):
    symbol:     str
    timeframe:  str
    swing_highs: List[SwingPointSchema] = []
    swing_lows:  List[SwingPointSchema] = []
    computed_at: Optional[datetime] = None
