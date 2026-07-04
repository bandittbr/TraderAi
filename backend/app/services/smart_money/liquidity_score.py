"""
Liquidity Score — Phase 7 (Smart Money Concepts)

Score composto 0–100 que integra todos os sinais de liquidez:
  - Liquidity Sweeps (presença e direção)
  - Fair Value Gaps (ativos próximos ao preço)
  - Volume Profile (HVN/LVN/VA position)
  - Proximidade de Suporte e Resistência (Phase 6.5)

Classificação:
  0–20  → Very Weak
  21–40 → Weak
  41–60 → Neutral
  61–80 → Strong
  81–100→ Very Strong

O score é calculado em relação a uma DIREÇÃO (BUY/SELL/NEUTRAL),
de forma que:
  - Para BUY:  score alto = liquidez institucional confirmando compra
  - Para SELL: score alto = liquidez institucional confirmando venda
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.smart_money.liquidity_sweep import SweepAnalysis
    from app.services.smart_money.fvg_engine      import FVGAnalysis
    from app.services.smart_money.volume_profile  import VolumeProfile


# ── Classificação ──────────────────────────────────────────────────────────────

class LiquidityLabel(str, enum.Enum):
    VERY_WEAK  = "Very Weak"
    WEAK       = "Weak"
    NEUTRAL    = "Neutral"
    STRONG     = "Strong"
    VERY_STRONG = "Very Strong"


def _label(score: float) -> LiquidityLabel:
    if score <= 20:   return LiquidityLabel.VERY_WEAK
    if score <= 40:   return LiquidityLabel.WEAK
    if score <= 60:   return LiquidityLabel.NEUTRAL
    if score <= 80:   return LiquidityLabel.STRONG
    return LiquidityLabel.VERY_STRONG


# ── Resultado ──────────────────────────────────────────────────────────────────

@dataclass
class LiquidityScoreResult:
    score:   float              # 0–100
    label:   LiquidityLabel
    # Contribuições por componente
    sweep_contribution:  float = 0.0
    fvg_contribution:    float = 0.0
    volume_contribution: float = 0.0
    sr_contribution:     float = 0.0
    # Detalhes
    direction:   str = "NEUTRAL"   # BUY | SELL | NEUTRAL
    reasons: List[str] = field(default_factory=list)
    # Flags para Signal Engine V5
    is_strong:     bool = False
    is_very_strong: bool = False


# ── Score principal ────────────────────────────────────────────────────────────

def compute_liquidity_score(
    direction:      str,              # "BUY" | "SELL" | "NEUTRAL"
    sweep_analysis  = None,           # SweepAnalysis | None
    fvg_analysis    = None,           # FVGAnalysis | None
    volume_profile  = None,           # VolumeProfile | None
    structure       = None,           # MarketStructureResult | None (Phase 6.5)
    # Pesos dos componentes (somam 100)
    sweep_weight:   float = 30.0,
    fvg_weight:     float = 25.0,
    volume_weight:  float = 25.0,
    sr_weight:      float = 20.0,
) -> LiquidityScoreResult:
    """
    Calcula o Liquidity Score para uma direção de operação.

    Args:
        direction:      "BUY", "SELL" ou "NEUTRAL"
        sweep_analysis: Resultado do Liquidity Sweep Detector
        fvg_analysis:   Resultado do FVG Engine
        volume_profile: Resultado do Volume Profile
        structure:      MarketStructureResult (Phase 6.5) para S/R

    Returns:
        LiquidityScoreResult com score 0–100 e label.
    """
    reasons: List[str] = []

    # ── Componente 1: Sweeps (30%) ─────────────────────────────────────────────
    sweep_raw = 0.0
    if sweep_analysis is not None:
        if direction == "BUY":
            if sweep_analysis.has_recent_buy_sweep:
                sweep_raw = 80.0
                reasons.append("Buy-side sweep recente confirmado")
                if sweep_analysis.recent_buy_sweep and sweep_analysis.recent_buy_sweep.is_stop_hunt:
                    sweep_raw = 100.0
                    reasons.append("Stop Hunt bullish detectado → máxima confluência")
            elif sweep_analysis.sweep_bias == "BULLISH":
                sweep_raw = 50.0
        elif direction == "SELL":
            if sweep_analysis.has_recent_sell_sweep:
                sweep_raw = 80.0
                reasons.append("Sell-side sweep recente confirmado")
                if sweep_analysis.recent_sell_sweep and sweep_analysis.recent_sell_sweep.is_stop_hunt:
                    sweep_raw = 100.0
                    reasons.append("Stop Hunt bearish detectado → máxima confluência")
            elif sweep_analysis.sweep_bias == "BEARISH":
                sweep_raw = 50.0
        elif direction == "NEUTRAL":
            sweep_raw = 50.0 if sweep_analysis.last_sweep else 30.0

    sweep_contrib = sweep_raw * sweep_weight / 100.0

    # ── Componente 2: FVG (25%) ────────────────────────────────────────────────
    fvg_raw = 0.0
    if fvg_analysis is not None:
        if direction == "BUY":
            if fvg_analysis.has_bullish_fvg:
                dist = fvg_analysis.bullish_fvg_distance_pct
                fvg_raw = max(0.0, 100.0 - dist * 10)
                reasons.append(f"Bullish FVG ativo a {dist:.2f}% do preço")
        elif direction == "SELL":
            if fvg_analysis.has_bearish_fvg:
                dist = fvg_analysis.bearish_fvg_distance_pct
                fvg_raw = max(0.0, 100.0 - dist * 10)
                reasons.append(f"Bearish FVG ativo a {dist:.2f}% do preço")

    fvg_contrib = fvg_raw * fvg_weight / 100.0

    # ── Componente 3: Volume Profile (25%) ────────────────────────────────────
    vol_raw = 0.0
    if volume_profile is not None:
        vol_raw = volume_profile.volume_profile_score
        if volume_profile.near_hvn:
            reasons.append(f"Preço próximo de HVN ({volume_profile.hvn_distance_pct:.2f}%)")
        if volume_profile.near_lvn:
            reasons.append(f"Preço em LVN — zona de baixa liquidez")
        if volume_profile.price_in_value_area:
            reasons.append("Preço dentro da Value Area")

    vol_contrib = vol_raw * volume_weight / 100.0

    # ── Componente 4: S/R Proximity (20%) ─────────────────────────────────────
    sr_raw = 50.0  # neutro por padrão
    if structure is not None:
        if direction == "BUY" and getattr(structure, "price_near_support", False):
            sr_raw = 80.0
            dist = getattr(structure, "support_distance_pct", 0.0)
            reasons.append(f"Preço próximo de suporte ({dist:.2f}%)")
        elif direction == "SELL" and getattr(structure, "price_near_resistance", False):
            sr_raw = 80.0
            dist = getattr(structure, "resistance_distance_pct", 0.0)
            reasons.append(f"Preço próximo de resistência ({dist:.2f}%)")
        elif direction == "BUY" and getattr(structure, "trend", None) is not None:
            trend_val = getattr(structure.trend, "value", str(structure.trend))
            if trend_val == "BULLISH":
                sr_raw = 70.0
        elif direction == "SELL" and getattr(structure, "trend", None) is not None:
            trend_val = getattr(structure.trend, "value", str(structure.trend))
            if trend_val == "BEARISH":
                sr_raw = 70.0

    sr_contrib = sr_raw * sr_weight / 100.0

    # ── Score final ────────────────────────────────────────────────────────────
    total = sweep_contrib + fvg_contrib + vol_contrib + sr_contrib
    total = round(max(0.0, min(100.0, total)), 1)
    label = _label(total)

    return LiquidityScoreResult(
        score              = total,
        label              = label,
        sweep_contribution = round(sweep_contrib, 2),
        fvg_contribution   = round(fvg_contrib, 2),
        volume_contribution = round(vol_contrib, 2),
        sr_contribution    = round(sr_contrib, 2),
        direction          = direction,
        reasons            = reasons,
        is_strong          = total >= 60,
        is_very_strong     = total >= 80,
    )
