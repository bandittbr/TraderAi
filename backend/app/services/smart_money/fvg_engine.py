"""
Fair Value Gap (FVG) Engine — Phase 7 (Smart Money Concepts)

Um Fair Value Gap (Imbalance) ocorre quando há um gap entre o candle i-2 e o
candle i que o candle intermediário (i-1) não preencheu totalmente.

Regras determinísticas:

  Bullish FVG:
    candle[i-2].high < candle[i].low
    → Gap entre o topo do candle pré-impulso e o fundo do candle pós-impulso
    → Instituições tipicamente voltam para recomprar nessa zona

  Bearish FVG:
    candle[i-2].low > candle[i].high
    → Gap entre o fundo do candle pré-impulso e o topo do candle pós-impulso
    → Instituições tipicamente voltam para vender nessa zona

Propriedades calculadas:
  gap_top / gap_bottom — limites da zona
  gap_size             — tamanho em pontos de preço
  gap_size_pct         — tamanho como % do preço
  is_filled            — se o preço já fechou dentro da zona
  fill_pct             — quanto do gap foi preenchido (0–100%)
  distance_pct         — distância do preço atual ao gap (%)
  relevance_score      — score 0–100 baseado em tamanho + recência + status
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional


# ── Tipos ──────────────────────────────────────────────────────────────────────

class FVGType(str, enum.Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class FVGStatus(str, enum.Enum):
    ACTIVE    = "ACTIVE"     # gap intacto, preço não entrou
    PARTIAL   = "PARTIAL"    # preço entrou mas não fechou dentro
    FILLED    = "FILLED"     # gap totalmente preenchido
    EXPIRED   = "EXPIRED"    # muito antigo (> max_age_candles)


# ── Estruturas ─────────────────────────────────────────────────────────────────

@dataclass
class FVGEvent:
    fvg_type:       FVGType
    status:         FVGStatus
    gap_top:        float          # limite superior do gap
    gap_bottom:     float          # limite inferior do gap
    gap_size:       float          # gap_top - gap_bottom (pontos)
    gap_size_pct:   float          # gap_size / midpoint * 100
    midpoint:       float          # (gap_top + gap_bottom) / 2
    candle_index:   int            # índice do candle i (candle que criou o gap)
    timestamp:      int            # timestamp do candle i
    is_filled:      bool  = False
    fill_pct:       float = 0.0    # 0–100%
    distance_pct:   float = 0.0    # % do preço atual até o gap
    relevance_score: float = 0.0   # 0–100
    reasons: List[str] = field(default_factory=list)


@dataclass
class FVGAnalysis:
    """Resultado completo da análise de FVGs."""
    all_fvgs:           List[FVGEvent]
    active_bullish:     List[FVGEvent]   # FVGs bullish não preenchidos
    active_bearish:     List[FVGEvent]   # FVGs bearish não preenchidos
    nearest_bullish:    Optional[FVGEvent] = None   # mais próximo do preço atual
    nearest_bearish:    Optional[FVGEvent] = None
    # Para Signal Engine V5
    has_bullish_fvg:    bool  = False    # FVG bullish ativo abaixo do preço
    has_bearish_fvg:    bool  = False    # FVG bearish ativo acima do preço
    bullish_fvg_distance_pct: float = 0.0
    bearish_fvg_distance_pct: float = 0.0


# ── Score de relevância ────────────────────────────────────────────────────────

def _relevance_score(fvg: FVGEvent, current_idx: int, current_price: float,
                     max_age: int) -> float:
    """
    Score 0–100 para relevância do FVG:
      - Tamanho do gap (maior = mais significativo)
      - Recência (mais recente = mais relevante)
      - Status (ativo > parcial > preenchido)
    """
    if fvg.status == FVGStatus.FILLED:
        return 0.0

    age = current_idx - fvg.candle_index
    age_score     = max(0.0, 1.0 - age / max_age)          # 0–1, decai com tempo
    size_score    = min(1.0, fvg.gap_size_pct / 0.5)       # normaliza em 0.5%
    status_score  = 1.0 if fvg.status == FVGStatus.ACTIVE else 0.5

    raw = (age_score * 0.4 + size_score * 0.4 + status_score * 0.2) * 100
    return round(min(100.0, raw), 1)


# ── Detector principal ─────────────────────────────────────────────────────────

def detect_fvgs(
    candles,
    current_price:     Optional[float] = None,
    proximity_pct:     float = 0.02,    # 2% — considera FVG "próximo"
    max_age_candles:   int   = 50,      # FVGs mais antigos são marcados EXPIRED
    min_gap_pct:       float = 0.0005,  # 0.05% mínimo para qualificar
) -> FVGAnalysis:
    """
    Detecta Fair Value Gaps na série de candles.

    Args:
        candles:        Lista de candles com high, low, close, timestamp.
        current_price:  Preço atual (padrão: último close).
        proximity_pct:  % de distância para considerar FVG como "próximo".
        max_age_candles: Candles após os quais o FVG é marcado como EXPIRED.
        min_gap_pct:    Tamanho mínimo do gap em % para não filtrar ruído.

    Returns:
        FVGAnalysis com todos os gaps classificados.
    """
    n = len(candles)
    if n < 3:
        return FVGAnalysis(all_fvgs=[], active_bullish=[], active_bearish=[])

    if current_price is None:
        current_price = candles[-1].close

    current_idx = n - 1
    all_fvgs: List[FVGEvent] = []

    for i in range(2, n):
        c0 = candles[i - 2]  # candle pré-impulso
        # c1 = candles[i - 1]  # candle impulso (não usado diretamente)
        c2 = candles[i]      # candle pós-impulso

        midpoint = (c0.high + c0.low + c2.high + c2.low) / 4

        # ── Bullish FVG ───────────────────────────────────────────────────────
        if c0.high < c2.low:
            gap_bottom = c0.high
            gap_top    = c2.low
            gap_size   = gap_top - gap_bottom
            gap_pct    = gap_size / midpoint * 100

            if gap_pct >= min_gap_pct * 100:
                age = current_idx - i
                status = _fvg_status_bullish(current_price, gap_top, gap_bottom, age, max_age_candles)
                fill_p = _fill_pct_bullish(current_price, gap_top, gap_bottom)
                dist_p = _distance_pct(current_price, gap_top, gap_bottom, "BULLISH")

                fvg = FVGEvent(
                    fvg_type    = FVGType.BULLISH,
                    status      = status,
                    gap_top     = gap_top,
                    gap_bottom  = gap_bottom,
                    gap_size    = gap_size,
                    gap_size_pct = gap_pct,
                    midpoint    = (gap_top + gap_bottom) / 2,
                    candle_index = i,
                    timestamp   = getattr(c2, "timestamp", i),
                    is_filled   = status == FVGStatus.FILLED,
                    fill_pct    = fill_p,
                    distance_pct = dist_p,
                    reasons     = [f"Bullish FVG: {c0.high:.2f}↔{c2.low:.2f} ({gap_pct:.3f}%)"],
                )
                fvg.relevance_score = _relevance_score(fvg, current_idx, current_price, max_age_candles)
                all_fvgs.append(fvg)

        # ── Bearish FVG ───────────────────────────────────────────────────────
        if c0.low > c2.high:
            gap_top    = c0.low
            gap_bottom = c2.high
            gap_size   = gap_top - gap_bottom
            gap_pct    = gap_size / midpoint * 100

            if gap_pct >= min_gap_pct * 100:
                age = current_idx - i
                status = _fvg_status_bearish(current_price, gap_top, gap_bottom, age, max_age_candles)
                fill_p = _fill_pct_bearish(current_price, gap_top, gap_bottom)
                dist_p = _distance_pct(current_price, gap_top, gap_bottom, "BEARISH")

                fvg = FVGEvent(
                    fvg_type    = FVGType.BEARISH,
                    status      = status,
                    gap_top     = gap_top,
                    gap_bottom  = gap_bottom,
                    gap_size    = gap_size,
                    gap_size_pct = gap_pct,
                    midpoint    = (gap_top + gap_bottom) / 2,
                    candle_index = i,
                    timestamp   = getattr(c2, "timestamp", i),
                    is_filled   = status == FVGStatus.FILLED,
                    fill_pct    = fill_p,
                    distance_pct = dist_p,
                    reasons     = [f"Bearish FVG: {c0.low:.2f}↔{c2.high:.2f} ({gap_pct:.3f}%)"],
                )
                fvg.relevance_score = _relevance_score(fvg, current_idx, current_price, max_age_candles)
                all_fvgs.append(fvg)

    # ── Filtrar e classificar ──────────────────────────────────────────────────
    active_bull = sorted(
        [f for f in all_fvgs
         if f.fvg_type == FVGType.BULLISH
         and f.status in (FVGStatus.ACTIVE, FVGStatus.PARTIAL)
         and f.gap_top < current_price],  # abaixo do preço atual (suporte potencial)
        key=lambda x: x.relevance_score, reverse=True,
    )
    active_bear = sorted(
        [f for f in all_fvgs
         if f.fvg_type == FVGType.BEARISH
         and f.status in (FVGStatus.ACTIVE, FVGStatus.PARTIAL)
         and f.gap_bottom > current_price],  # acima do preço atual (resistência potencial)
        key=lambda x: x.relevance_score, reverse=True,
    )

    nearest_bull = active_bull[0] if active_bull else None
    nearest_bear = active_bear[0] if active_bear else None

    # Considera "próximo" se dentro de proximity_pct
    has_bull = (
        nearest_bull is not None and
        nearest_bull.distance_pct <= proximity_pct * 100
    )
    has_bear = (
        nearest_bear is not None and
        nearest_bear.distance_pct <= proximity_pct * 100
    )

    return FVGAnalysis(
        all_fvgs              = all_fvgs,
        active_bullish        = active_bull[:5],   # top 5
        active_bearish        = active_bear[:5],
        nearest_bullish       = nearest_bull,
        nearest_bearish       = nearest_bear,
        has_bullish_fvg       = has_bull,
        has_bearish_fvg       = has_bear,
        bullish_fvg_distance_pct = nearest_bull.distance_pct if nearest_bull else 0.0,
        bearish_fvg_distance_pct = nearest_bear.distance_pct if nearest_bear else 0.0,
    )


# ── Helpers de status e fill ───────────────────────────────────────────────────

def _fvg_status_bullish(price: float, top: float, bot: float, age: int, max_age: int) -> FVGStatus:
    if age > max_age:
        return FVGStatus.EXPIRED
    if price <= bot:
        return FVGStatus.FILLED
    if bot < price < top:
        return FVGStatus.PARTIAL
    return FVGStatus.ACTIVE


def _fvg_status_bearish(price: float, top: float, bot: float, age: int, max_age: int) -> FVGStatus:
    if age > max_age:
        return FVGStatus.EXPIRED
    if price >= top:
        return FVGStatus.FILLED
    if bot < price < top:
        return FVGStatus.PARTIAL
    return FVGStatus.ACTIVE


def _fill_pct_bullish(price: float, top: float, bot: float) -> float:
    gap = top - bot
    if gap <= 0:
        return 100.0
    if price >= top:
        return 100.0
    if price <= bot:
        return 0.0
    return (top - price) / gap * 100


def _fill_pct_bearish(price: float, top: float, bot: float) -> float:
    gap = top - bot
    if gap <= 0:
        return 100.0
    if price <= bot:
        return 100.0
    if price >= top:
        return 0.0
    return (price - bot) / gap * 100


def _distance_pct(price: float, top: float, bot: float, direction: str) -> float:
    if direction == "BULLISH":
        # distância do preço até o topo do gap (acima)
        if price > top:
            return (price - top) / price * 100
        return 0.0
    else:
        # distância do preço até o fundo do gap (abaixo)
        if price < bot:
            return (bot - price) / price * 100
        return 0.0
