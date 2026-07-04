"""
Break of Structure (BOS) Detector — Phase 6.5

Break of Structure:
  BOS Bullish : preço atual rompe ACIMA do último Swing High significativo
                → confirma continuação ou inversão para BULLISH
  BOS Bearish : preço atual rompe ABAIXO do último Swing Low significativo
                → confirma continuação ou inversão para BEARISH

Diferença entre BOS e CHoCH (Change of Character):
  BOS    : rompimento na direção da tendência atual (continuação)
  CHoCH  : rompimento contra a tendência (possível reversão)
  → Para simplidade e determinismo, detectamos ambos como BOS + flag de reversão.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.services.market_structure.swing_detector import SwingPoint
from app.services.market_structure.structure_classifier import StructureResult, StructureTrend


@dataclass
class BOSResult:
    """Resultado da detecção de Break of Structure."""
    bos_bullish:    bool    = False     # rompeu acima do último swing high
    bos_bearish:    bool    = False     # rompeu abaixo do último swing low

    broke_level:    Optional[float] = None  # nível rompido
    broke_side:     Optional[str]   = None  # "BULLISH" | "BEARISH"

    # Contexto estrutural da quebra
    is_choch:       bool = False    # True se rompeu contra a tendência (reversão)
    bos_strength:   float = 0.0     # % acima/abaixo do nível rompido

    key_level_high: Optional[float] = None  # último swing high de referência
    key_level_low:  Optional[float] = None  # último swing low de referência

    reasons: list[str] = field(default_factory=list)


def detect_bos(
    current_price:    float,
    swing_highs:      list[SwingPoint],
    swing_lows:       list[SwingPoint],
    structure:        Optional[StructureResult] = None,
    bos_tolerance:    float = 0.001,   # 0.1% de tolerância p/ confirmar rompimento
) -> BOSResult:
    """
    Detecta Break of Structure comparando o preço atual com os últimos pivôs.

    Args:
        current_price:  preço atual do ativo
        swing_highs:    lista de swing highs detectados
        swing_lows:     lista de swing lows detectados
        structure:      resultado da classificação estrutural (para CHoCH)
        bos_tolerance:  % mínimo acima/abaixo do nível para confirmar BOS

    Returns:
        BOSResult com flags e detalhes do rompimento.
    """
    result = BOSResult()

    if not swing_highs and not swing_lows:
        result.reasons.append("Sem swings disponíveis para detectar BOS")
        return result

    # Nível de referência: último swing high e swing low
    key_high = swing_highs[-1].price if swing_highs else None
    key_low  = swing_lows[-1].price  if swing_lows  else None

    result.key_level_high = key_high
    result.key_level_low  = key_low

    # ── BOS Bullish: preço acima do último swing high ────────────────────────
    if key_high is not None:
        min_break = key_high * (1 + bos_tolerance)
        if current_price > min_break:
            result.bos_bullish  = True
            result.broke_level  = key_high
            result.broke_side   = "BULLISH"
            strength = ((current_price - key_high) / key_high) * 100
            result.bos_strength = round(strength, 3)
            result.reasons.append(
                f"BOS Bullish: preco {current_price:.2f} > key_high {key_high:.2f} "
                f"(+{strength:.2f}%)"
            )

            # CHoCH: rompeu bullish mas tendência era bearish
            if structure and structure.trend == StructureTrend.BEARISH:
                result.is_choch = True
                result.reasons.append("CHoCH detectado: inversão de BEARISH para BULLISH")

    # ── BOS Bearish: preço abaixo do último swing low ────────────────────────
    if key_low is not None:
        max_break = key_low * (1 - bos_tolerance)
        if current_price < max_break:
            result.bos_bearish  = True
            result.broke_level  = key_low
            result.broke_side   = "BEARISH"
            strength = ((key_low - current_price) / key_low) * 100
            result.bos_strength = round(strength, 3)
            result.reasons.append(
                f"BOS Bearish: preco {current_price:.2f} < key_low {key_low:.2f} "
                f"(-{strength:.2f}%)"
            )

            # CHoCH: rompeu bearish mas tendência era bullish
            if structure and structure.trend == StructureTrend.BULLISH:
                result.is_choch = True
                result.reasons.append("CHoCH detectado: inversão de BULLISH para BEARISH")

    if not result.bos_bullish and not result.bos_bearish:
        result.reasons.append(
            f"Sem BOS: preco {current_price:.2f} dentro de "
            f"[{key_low:.2f}, {key_high:.2f}]"
            if key_low and key_high else "Sem BOS detectado"
        )

    return result
