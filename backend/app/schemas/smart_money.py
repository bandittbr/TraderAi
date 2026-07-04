"""Pydantic v2 — Schemas Smart Money Phase 7"""
from __future__ import annotations
from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SweepEventSchema(BaseModel):
    sweep_type:      str
    strength:        str
    price:           float
    swept_level:     float
    timestamp:       int
    penetration_pct: float
    is_stop_hunt:    bool


class FVGSchema(BaseModel):
    fvg_type:    str
    status:      str
    gap_top:     float
    gap_bottom:  float
    gap_size_pct: float
    distance_pct: float
    relevance:   float
    is_filled:   bool


class SmartMoneyResponse(BaseModel):
    symbol:    str
    timeframe: str

    # Sweeps
    has_recent_buy_sweep:  bool  = False
    has_recent_sell_sweep: bool  = False
    sweep_bias:            str   = "NEUTRAL"
    last_sweep_type:       Optional[str]   = None
    last_sweep_price:      Optional[float] = None
    last_sweep_timestamp:  Optional[int]   = None
    recent_sweeps:         List[SweepEventSchema] = []

    # FVG
    has_bullish_fvg:          bool  = False
    has_bearish_fvg:          bool  = False
    bullish_fvg_top:          Optional[float] = None
    bullish_fvg_bottom:       Optional[float] = None
    bullish_fvg_distance_pct: float = 0.0
    bearish_fvg_top:          Optional[float] = None
    bearish_fvg_bottom:       Optional[float] = None
    bearish_fvg_distance_pct: float = 0.0
    active_fvgs:              List[FVGSchema] = []

    # Volume Profile
    volume_profile_score: float = 50.0
    poc:                  Optional[float] = None
    value_area_high:      Optional[float] = None
    value_area_low:       Optional[float] = None
    hvn_levels:           List[float] = []
    lvn_levels:           List[float] = []
    near_hvn:             bool  = False
    near_lvn:             bool  = False
    price_in_value_area:  bool  = False

    # Liquidity Score
    liquidity_score: float = Field(50.0, ge=0, le=100)
    liquidity_label: str   = "Neutral"
    liq_score_strong: bool = False

    candles_analyzed: int = 0
    computed_at: Optional[datetime] = None


class SweepsResponse(BaseModel):
    symbol: str; timeframe: str
    events: List[SweepEventSchema] = []
    buy_count: int = 0; sell_count: int = 0
    sweep_bias: str = "NEUTRAL"
    computed_at: Optional[datetime] = None


class FVGsResponse(BaseModel):
    symbol: str; timeframe: str
    active_bullish: List[FVGSchema] = []
    active_bearish: List[FVGSchema] = []
    has_bullish_fvg: bool = False
    has_bearish_fvg: bool = False
    computed_at: Optional[datetime] = None


class VolumeProfileResponse(BaseModel):
    symbol: str; timeframe: str
    volume_profile_score: float = 50.0
    poc: Optional[float] = None
    value_area_high: Optional[float] = None
    value_area_low:  Optional[float] = None
    hvn_levels: List[float] = []
    lvn_levels: List[float] = []
    near_hvn: bool = False; near_lvn: bool = False
    price_in_value_area: bool = False
    computed_at: Optional[datetime] = None
