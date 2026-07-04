"""
Volume Profile Lite — Phase 7 (Smart Money Concepts)

Constrói um perfil de volume simplificado a partir dos candles armazenados.
Não requer dados tick-by-tick — usa o volume por candle distribuído
proporcionalmente ao range do candle.

Metodologia:
  1. Divide o range de preço em N bins (padrão 50)
  2. Para cada candle: distribui seu volume entre os bins que seu range cobre
     usando ponderação proporcional ao overlap
  3. Calcula HVN (High Volume Nodes) e LVN (Low Volume Nodes)
  4. Determina Value Area (VA) = bins com 70% do volume total

Saídas:
  hvn_levels     — preços dos HVNs mais fortes
  lvn_levels     — preços dos LVNs mais vazios
  value_area_high (VAH)
  value_area_low  (VAL)
  point_of_control (POC) — preço com maior volume
  volume_profile_score   — 0–100 baseado na posição do preço relativa ao perfil
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ── Estruturas ─────────────────────────────────────────────────────────────────

@dataclass
class VolumeNode:
    price:      float       # preço central do bin
    volume:     float       # volume total no bin
    pct_total:  float       # % do volume total
    is_hvn:     bool = False
    is_lvn:     bool = False


@dataclass
class VolumeProfile:
    """Resultado do Volume Profile Lite."""
    nodes:          List[VolumeNode]
    hvn_levels:     List[float]      # preços dos HVNs (até 5)
    lvn_levels:     List[float]      # preços dos LVNs (até 5)
    point_of_control: float          # POC — preço com mais volume
    value_area_high:  float          # VAH — limite superior da Value Area
    value_area_low:   float          # VAL — limite inferior da Value Area
    current_price:    float
    # Posição relativa ao perfil
    price_in_value_area: bool = False
    price_above_poc:     bool = False
    near_hvn:            bool = False
    near_lvn:            bool = False
    hvn_distance_pct:    float = 0.0
    lvn_distance_pct:    float = 0.0
    # Score 0–100
    volume_profile_score: float = 50.0
    # Meta
    bins_used:     int   = 0
    candles_used:  int   = 0
    price_range_pct: float = 0.0


# ── Construtor do perfil ───────────────────────────────────────────────────────

def compute_volume_profile(
    candles,
    current_price:    Optional[float] = None,
    n_bins:           int   = 50,
    value_area_pct:   float = 0.70,   # 70% do volume = Value Area
    hvn_threshold:    float = 1.5,    # bins com vol > 1.5× média = HVN
    lvn_threshold:    float = 0.4,    # bins com vol < 0.4× média = LVN
    proximity_pct:    float = 0.005,  # 0.5% — "próximo" de um nível
    max_hvn:          int   = 5,
    max_lvn:          int   = 5,
) -> VolumeProfile:
    """
    Constrói o Volume Profile a partir dos candles.

    Args:
        candles:        Lista de candles com high, low, close, volume.
        current_price:  Preço atual (padrão: último close).
        n_bins:         Número de bins para dividir o range.
        value_area_pct: Percentual do volume total que define a Value Area.
        hvn_threshold:  Múltiplo da média para classificar como HVN.
        lvn_threshold:  Múltiplo da média para classificar como LVN.
        proximity_pct:  % de distância para "próximo de HVN/LVN".
        max_hvn/max_lvn: Máximo de níveis a retornar.

    Returns:
        VolumeProfile completo.
    """
    if not candles:
        return VolumeProfile(
            nodes=[], hvn_levels=[], lvn_levels=[],
            point_of_control=0, value_area_high=0, value_area_low=0,
            current_price=0,
        )

    if current_price is None:
        current_price = candles[-1].close

    # ── 1. Range de preço ─────────────────────────────────────────────────────
    price_high = max(c.high for c in candles)
    price_low  = min(c.low  for c in candles)
    price_range = price_high - price_low

    if price_range <= 0:
        poc = current_price
        return VolumeProfile(
            nodes=[], hvn_levels=[], lvn_levels=[],
            point_of_control=poc, value_area_high=poc, value_area_low=poc,
            current_price=current_price,
        )

    bin_size   = price_range / n_bins
    bin_volume = [0.0] * n_bins

    # ── 2. Distribuir volume nos bins ─────────────────────────────────────────
    for c in candles:
        candle_range = c.high - c.low
        vol = getattr(c, "volume", 1.0) or 1.0

        if candle_range <= 0:
            # Candle doji — tudo no bin mais próximo
            idx = min(int((c.close - price_low) / bin_size), n_bins - 1)
            bin_volume[idx] += vol
            continue

        # Distribui proporcionalmente ao overlap do candle com cada bin
        for b in range(n_bins):
            bin_low  = price_low + b * bin_size
            bin_high = bin_low + bin_size
            overlap  = min(c.high, bin_high) - max(c.low, bin_low)
            if overlap > 0:
                bin_volume[b] += vol * (overlap / candle_range)

    total_volume = sum(bin_volume)
    if total_volume <= 0:
        total_volume = 1.0

    # ── 3. Construir nodes ────────────────────────────────────────────────────
    avg_vol = total_volume / n_bins
    nodes: List[VolumeNode] = []
    for b in range(n_bins):
        mid = price_low + (b + 0.5) * bin_size
        pct = bin_volume[b] / total_volume * 100
        nodes.append(VolumeNode(
            price     = mid,
            volume    = bin_volume[b],
            pct_total = pct,
            is_hvn    = bin_volume[b] >= avg_vol * hvn_threshold,
            is_lvn    = bin_volume[b] <= avg_vol * lvn_threshold and bin_volume[b] > 0,
        ))

    # ── 4. POC ────────────────────────────────────────────────────────────────
    poc_node = max(nodes, key=lambda x: x.volume)
    poc      = poc_node.price

    # ── 5. Value Area (70% do volume a partir do POC) ─────────────────────────
    poc_idx    = nodes.index(poc_node)
    target_vol = total_volume * value_area_pct
    va_vol     = bin_volume[poc_idx]
    va_low_idx = poc_idx
    va_high_idx = poc_idx

    while va_vol < target_vol:
        expand_up   = va_high_idx + 1 < n_bins
        expand_down = va_low_idx  - 1 >= 0

        if not expand_up and not expand_down:
            break

        vol_up   = bin_volume[va_high_idx + 1] if expand_up   else 0
        vol_down = bin_volume[va_low_idx  - 1] if expand_down else 0

        if vol_up >= vol_down and expand_up:
            va_high_idx += 1
            va_vol += vol_up
        elif expand_down:
            va_low_idx -= 1
            va_vol += vol_down
        else:
            va_high_idx += 1
            va_vol += vol_up

    vah = nodes[va_high_idx].price + bin_size / 2
    val = nodes[va_low_idx].price  - bin_size / 2

    # ── 6. HVN e LVN levels ───────────────────────────────────────────────────
    hvns = sorted([n for n in nodes if n.is_hvn], key=lambda x: x.volume, reverse=True)
    lvns = sorted([n for n in nodes if n.is_lvn], key=lambda x: x.volume)

    hvn_levels = [n.price for n in hvns[:max_hvn]]
    lvn_levels = [n.price for n in lvns[:max_lvn]]

    # ── 7. Proximidade ────────────────────────────────────────────────────────
    def nearest_distance(levels: List[float]) -> float:
        if not levels:
            return 999.0
        return min(abs(current_price - lvl) / current_price * 100 for lvl in levels)

    hvn_dist = nearest_distance(hvn_levels)
    lvn_dist = nearest_distance(lvn_levels)
    near_hvn = hvn_dist <= proximity_pct * 100
    near_lvn = lvn_dist <= proximity_pct * 100

    # ── 8. Volume Profile Score ───────────────────────────────────────────────
    score = _compute_score(
        current_price, poc, vah, val,
        hvn_levels, lvn_levels,
        hvn_dist, lvn_dist,
        near_hvn, near_lvn,
        price_low, price_high,
    )

    return VolumeProfile(
        nodes               = nodes,
        hvn_levels          = hvn_levels,
        lvn_levels          = lvn_levels,
        point_of_control    = poc,
        value_area_high     = vah,
        value_area_low      = val,
        current_price       = current_price,
        price_in_value_area = val <= current_price <= vah,
        price_above_poc     = current_price > poc,
        near_hvn            = near_hvn,
        near_lvn            = near_lvn,
        hvn_distance_pct    = hvn_dist,
        lvn_distance_pct    = lvn_dist,
        volume_profile_score = score,
        bins_used           = n_bins,
        candles_used        = len(candles),
        price_range_pct     = price_range / current_price * 100,
    )


def _compute_score(
    price: float, poc: float, vah: float, val: float,
    hvns: List[float], lvns: List[float],
    hvn_dist: float, lvn_dist: float,
    near_hvn: bool, near_lvn: bool,
    price_low: float, price_high: float,
) -> float:
    """
    Calcula volume_profile_score (0–100).

    Critérios:
      50 base
      +20 se preço está na Value Area
      +15 se preço está próximo de HVN (suporte/resistência forte)
      -10 se preço está em LVN (zona de baixa liquidez, move rápido)
      +15 se preço está acima do POC (força institucional)
    """
    score = 50.0

    if val <= price <= vah:
        score += 20.0
    if near_hvn:
        score += 15.0
    if near_lvn:
        score -= 10.0
    if price > poc:
        score += 15.0

    return round(max(0.0, min(100.0, score)), 1)
