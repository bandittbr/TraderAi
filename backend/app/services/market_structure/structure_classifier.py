"""
Market Structure Classifier — Phase 6.5

Classifica a tendência estrutural do mercado usando os swings detectados:

  Higher High  (HH): topo atual > topo anterior  → bullish
  Higher Low   (HL): fundo atual > fundo anterior → bullish
  Lower High   (LH): topo atual < topo anterior   → bearish
  Lower Low    (LL): fundo atual < fundo anterior  → bearish

Tendência estrutural:
  BULLISH  : predominância de HH + HL
  BEARISH  : predominância de LH + LL
  RANGING  : sem predominância clara (misturado)
  UNDEFINED: dados insuficientes (< 2 swings de cada tipo)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional

from app.services.market_structure.swing_detector import SwingPoint


# ─────────────────────────────────────────────
# Enums e tipos
# ─────────────────────────────────────────────

class StructureTrend(str, enum.Enum):
    BULLISH   = "BULLISH"
    BEARISH   = "BEARISH"
    RANGING   = "RANGING"
    UNDEFINED = "UNDEFINED"


class SwingLabel(str, enum.Enum):
    HH = "HH"   # Higher High
    HL = "HL"   # Higher Low
    LH = "LH"   # Lower High
    LL = "LL"   # Lower Low


@dataclass
class LabeledSwing:
    point:     SwingPoint
    label:     SwingLabel
    prev_price: float   # preço do swing anterior (para referência)


@dataclass
class StructureResult:
    """Resultado completo da classificação de estrutura."""
    trend:            StructureTrend
    confidence:       float             # 0–100%

    # Últimos swings classificados
    labeled_highs:    list[LabeledSwing] = field(default_factory=list)
    labeled_lows:     list[LabeledSwing] = field(default_factory=list)

    # Contagens
    hh_count:   int = 0
    hl_count:   int = 0
    lh_count:   int = 0
    ll_count:   int = 0

    # Últimos valores concretos
    last_swing_high:  Optional[float] = None   # preço do topo mais recente
    last_swing_low:   Optional[float] = None   # preço do fundo mais recente
    prev_swing_high:  Optional[float] = None   # topo anterior
    prev_swing_low:   Optional[float] = None   # fundo anterior

    # Label do topo e fundo mais recentes
    last_high_label:  Optional[str]   = None   # "HH" | "LH"
    last_low_label:   Optional[str]   = None   # "HL" | "LL"

    # Texto descritivo para exibição
    structure_label:  str = ""        # ex: "HH+HL", "LH+LL", "HH+LL"

    reasons:    list[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# Classificação
# ─────────────────────────────────────────────

def _label_sequence(prices: list[float]) -> list[SwingLabel]:
    """
    Rotula uma sequência de preços de swing do mesmo tipo (HIGH ou LOW).
    Retorna HH/LH para highs ou HL/LL para lows.
    """
    if len(prices) < 2:
        return []

    labels = []
    is_high = True   # será corrigido pelo chamador, aqui só calcula comparação

    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            labels.append("UP")
        elif prices[i] < prices[i - 1]:
            labels.append("DOWN")
        else:
            labels.append("EQUAL")
    return labels


def classify_structure(
    swing_highs: list[SwingPoint],
    swing_lows:  list[SwingPoint],
    lookback:    int = 4,   # quantos swings recentes usar
) -> StructureResult:
    """
    Classifica a estrutura de mercado a partir dos swings detectados.

    Args:
        swing_highs: lista de SwingPoints do tipo HIGH (ordem cronológica)
        swing_lows:  lista de SwingPoints do tipo LOW  (ordem cronológica)
        lookback:    nº de swings recentes para análise (mínimo 2)

    Returns:
        StructureResult com tendência, confidence e detalhes.
    """
    # Requer pelo menos 2 highs E 2 lows
    if len(swing_highs) < 2 or len(swing_lows) < 2:
        return StructureResult(
            trend=StructureTrend.UNDEFINED,
            confidence=0.0,
            reasons=["Swings insuficientes (mínimo 2 topos e 2 fundos)"],
        )

    # Usa apenas os últimos N swings de cada tipo
    recent_highs = swing_highs[-lookback:]
    recent_lows  = swing_lows[-lookback:]

    # ── Classificar topos ────────────────────────────────────────────────────
    labeled_highs: list[LabeledSwing] = []
    hh_count = lh_count = 0

    for i in range(1, len(recent_highs)):
        curr = recent_highs[i]
        prev = recent_highs[i - 1]
        label = SwingLabel.HH if curr.price > prev.price else SwingLabel.LH
        labeled_highs.append(LabeledSwing(point=curr, label=label, prev_price=prev.price))
        if label == SwingLabel.HH:
            hh_count += 1
        else:
            lh_count += 1

    # ── Classificar fundos ───────────────────────────────────────────────────
    labeled_lows: list[LabeledSwing] = []
    hl_count = ll_count = 0

    for i in range(1, len(recent_lows)):
        curr = recent_lows[i]
        prev = recent_lows[i - 1]
        label = SwingLabel.HL if curr.price > prev.price else SwingLabel.LL
        labeled_lows.append(LabeledSwing(point=curr, label=label, prev_price=prev.price))
        if label == SwingLabel.HL:
            hl_count += 1
        else:
            ll_count += 1

    # ── Determinar tendência ─────────────────────────────────────────────────
    bull_score = hh_count + hl_count
    bear_score = lh_count + ll_count
    total      = bull_score + bear_score

    last_high_label = labeled_highs[-1].label.value if labeled_highs else None
    last_low_label  = labeled_lows[-1].label.value  if labeled_lows  else None

    if total == 0:
        trend = StructureTrend.UNDEFINED
        confidence = 0.0
    elif bull_score > bear_score:
        trend = StructureTrend.BULLISH
        confidence = round((bull_score / total) * 100, 1)
    elif bear_score > bull_score:
        trend = StructureTrend.BEARISH
        confidence = round((bear_score / total) * 100, 1)
    else:
        trend = StructureTrend.RANGING
        confidence = 50.0

    # ── Estrutura composta dos 2 swings mais recentes ────────────────────────
    last_h = last_high_label or "?"
    last_l = last_low_label  or "?"
    structure_label = f"{last_h}+{last_l}"

    # ── Razões (auditáveis) ──────────────────────────────────────────────────
    reasons = [
        f"HH={hh_count} HL={hl_count} (bull_score={bull_score})",
        f"LH={lh_count} LL={ll_count} (bear_score={bear_score})",
        f"Último topo: {last_high_label} | Último fundo: {last_low_label}",
        f"Tendência estrutural: {trend.value} ({confidence:.0f}% confiança)",
    ]

    return StructureResult(
        trend           = trend,
        confidence      = confidence,
        labeled_highs   = labeled_highs,
        labeled_lows    = labeled_lows,
        hh_count        = hh_count,
        hl_count        = hl_count,
        lh_count        = lh_count,
        ll_count        = ll_count,
        last_swing_high = recent_highs[-1].price if recent_highs else None,
        last_swing_low  = recent_lows[-1].price  if recent_lows  else None,
        prev_swing_high = recent_highs[-2].price if len(recent_highs) >= 2 else None,
        prev_swing_low  = recent_lows[-2].price  if len(recent_lows)  >= 2 else None,
        last_high_label = last_high_label,
        last_low_label  = last_low_label,
        structure_label = structure_label,
        reasons         = reasons,
    )
