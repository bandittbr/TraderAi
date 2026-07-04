"""
Support & Resistance Zones — Phase 6.5

Calcula zonas de suporte e resistência a partir de clusters de pivôs (swing highs/lows).

Algoritmo:
  1. Coleta todos os swing highs (resistências) e swing lows (suportes)
  2. Agrupa pivôs próximos (dentro de cluster_tolerance%) em uma zona
  3. Ordena zonas por força (nº de toques e recência)
  4. Calcula se o preço atual está próximo de alguma zona (zona_proximity%)

Zona forte = tocada 3+ vezes historicamente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from app.services.market_structure.swing_detector import SwingPoint


# ─────────────────────────────────────────────
# Tipos
# ─────────────────────────────────────────────

@dataclass
class SRZone:
    """Uma zona de suporte ou resistência."""
    level:       float                       # preço central da zona
    zone_type:   Literal["SUPPORT", "RESISTANCE"]
    touch_count: int                         # quantas vezes o preço tocou
    strength:    Literal["WEAK", "MODERATE", "STRONG"]
    range_low:   float                       # limite inferior da zona
    range_high:  float                       # limite superior da zona
    last_touch_idx: int                      # index do último toque (candle)
    contributing_swings: list[float] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"{self.zone_type[:3]} {self.level:.0f} ({self.touch_count}x {self.strength})"


@dataclass
class SRAnalysis:
    """Resultado da análise de suporte e resistência."""
    support_zones:    list[SRZone]           # zonas abaixo do preço atual
    resistance_zones: list[SRZone]           # zonas acima do preço atual
    nearest_support:  Optional[SRZone]       # suporte mais próximo
    nearest_resistance: Optional[SRZone]     # resistência mais próxima
    price_near_support:    bool = False       # preço dentro da zona de suporte
    price_near_resistance: bool = False       # preço dentro da zona de resistência
    support_distance_pct:    float = 0.0     # % até o suporte mais próximo
    resistance_distance_pct: float = 0.0     # % até a resistência mais próxima


# ─────────────────────────────────────────────
# Funções
# ─────────────────────────────────────────────

def _strength(touch_count: int) -> Literal["WEAK", "MODERATE", "STRONG"]:
    if touch_count >= 4:
        return "STRONG"
    if touch_count >= 2:
        return "MODERATE"
    return "WEAK"


def _cluster_pivots(
    pivots: list[SwingPoint],
    cluster_tolerance: float,   # % de tolerância para agrupar
    zone_type: Literal["SUPPORT", "RESISTANCE"],
) -> list[SRZone]:
    """
    Agrupa pivôs próximos em zonas.
    Percorre de cima para baixo (preço) para resistências,
    de baixo para cima para suportes.
    """
    if not pivots:
        return []

    # Ordena por preço
    sorted_pivots = sorted(pivots, key=lambda p: p.price, reverse=(zone_type == "RESISTANCE"))

    zones: list[SRZone] = []
    used   = set()

    for i, pivot in enumerate(sorted_pivots):
        if i in used:
            continue

        # Inicia um novo cluster com este pivô
        cluster_prices = [pivot.price]
        cluster_idxs   = [pivot.index]
        used.add(i)

        ref_price = pivot.price

        # Agrupa pivôs próximos
        for j, other in enumerate(sorted_pivots):
            if j in used:
                continue
            if abs(other.price - ref_price) / ref_price <= cluster_tolerance:
                cluster_prices.append(other.price)
                cluster_idxs.append(other.index)
                used.add(j)

        level      = sum(cluster_prices) / len(cluster_prices)
        tolerance  = level * cluster_tolerance
        touch_count = len(cluster_prices)

        zones.append(SRZone(
            level       = round(level, 2),
            zone_type   = zone_type,
            touch_count = touch_count,
            strength    = _strength(touch_count),
            range_low   = round(level - tolerance, 2),
            range_high  = round(level + tolerance, 2),
            last_touch_idx = max(cluster_idxs),
            contributing_swings = [round(p, 2) for p in sorted(cluster_prices)],
        ))

    # Ordena por força (toque + recência)
    zones.sort(key=lambda z: (z.touch_count, z.last_touch_idx), reverse=True)
    return zones


def compute_sr_zones(
    swing_highs:       list[SwingPoint],
    swing_lows:        list[SwingPoint],
    current_price:     float,
    cluster_tolerance: float = 0.005,   # 0.5% — pivôs dentro desse range = mesma zona
    proximity_pct:     float = 0.015,   # 1.5% — preço "dentro" da zona
    max_zones:         int   = 5,        # máximo de zonas de cada tipo
) -> SRAnalysis:
    """
    Calcula zonas de suporte e resistência a partir dos swings.

    Args:
        swing_highs:       topos detectados (→ resistências)
        swing_lows:        fundos detectados (→ suportes)
        current_price:     preço atual para classificar sup/res e proximity
        cluster_tolerance: % para agrupar pivôs na mesma zona
        proximity_pct:     % para considerar preço "dentro" de uma zona
        max_zones:         máximo de zonas a retornar por tipo

    Returns:
        SRAnalysis com zonas e análise de proximidade.
    """
    # Zonas de resistência (acima do preço) = cluster de swing highs
    all_resistance = _cluster_pivots(swing_highs, cluster_tolerance, "RESISTANCE")
    # Zonas de suporte (abaixo do preço) = cluster de swing lows
    all_support    = _cluster_pivots(swing_lows,  cluster_tolerance, "SUPPORT")

    # Filtra por posição relativa ao preço atual
    resistance_zones = sorted(
        [z for z in all_resistance if z.level > current_price],
        key=lambda z: z.level,          # mais próximo primeiro
    )[:max_zones]

    support_zones = sorted(
        [z for z in all_support if z.level < current_price],
        key=lambda z: z.level,
        reverse=True,                   # mais próximo primeiro (maior valor)
    )[:max_zones]

    # Zona mais próxima de cada tipo
    nearest_sup = support_zones[0]    if support_zones    else None
    nearest_res = resistance_zones[0] if resistance_zones else None

    # Proximidade
    near_sup = near_res = False
    sup_dist  = res_dist = 0.0

    if nearest_sup:
        sup_dist = ((current_price - nearest_sup.level) / current_price) * 100
        near_sup = sup_dist <= proximity_pct * 100

    if nearest_res:
        res_dist = ((nearest_res.level - current_price) / current_price) * 100
        near_res = res_dist <= proximity_pct * 100

    return SRAnalysis(
        support_zones            = support_zones,
        resistance_zones         = resistance_zones,
        nearest_support          = nearest_sup,
        nearest_resistance       = nearest_res,
        price_near_support       = near_sup,
        price_near_resistance    = near_res,
        support_distance_pct     = round(sup_dist, 2),
        resistance_distance_pct  = round(res_dist, 2),
    )
