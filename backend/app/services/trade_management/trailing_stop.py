"""
TradeAI — Trailing Stop Engine (Fase 12)

Ativa quando o trade atinge paper_trailing_start_pct de lucro.
Segue o preço mantendo paper_trailing_distance_pct de distância do pico.

LONG:
  trailing_stop_peak  = máximo preço visto
  trailing_stop_price = peak * (1 - distance_pct)
  Hit: current_price <= trailing_stop_price

SHORT:
  trailing_stop_peak  = mínimo preço visto
  trailing_stop_price = peak * (1 + distance_pct)
  Hit: current_price >= trailing_stop_price

Determinístico — sem randomicidade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import settings


@dataclass
class TrailingState:
    active:       bool
    peak:         Optional[float]
    stop_price:   Optional[float]
    updated:      bool  # True se houve atualização nesta chamada


def compute(
    side: str,
    entry_price: float,
    current_price: float,
    current_peak: Optional[float],
    current_stop: Optional[float],
    currently_active: bool,
) -> TrailingState:
    """
    Calcula o novo estado do trailing stop.
    Retorna TrailingState com updated=True se houve mudança.
    """
    start_pct = settings.paper_trailing_start_pct / 100
    dist_pct  = settings.paper_trailing_distance_pct / 100

    # Verifica se deve ativar
    if side == "LONG":
        should_start = current_price >= entry_price * (1 + start_pct)
    else:
        should_start = current_price <= entry_price * (1 - start_pct)

    if not should_start and not currently_active:
        return TrailingState(active=False, peak=None, stop_price=None, updated=False)

    # Calcula novo peak
    if side == "LONG":
        new_peak = max(current_peak or entry_price, current_price)
        new_stop = new_peak * (1 - dist_pct)
    else:
        new_peak = min(current_peak or entry_price, current_price)
        new_stop = new_peak * (1 + dist_pct)

    # Verifica se houve atualização relevante (> 0.01% mudança)
    updated = (
        not currently_active
        or abs((new_peak or 0) - (current_peak or 0)) > entry_price * 0.0001
    )

    return TrailingState(
        active=True,
        peak=round(new_peak, 8),
        stop_price=round(new_stop, 8),
        updated=updated,
    )


def check_hit(
    side: str,
    current_price: float,
    trailing_stop_price: Optional[float],
    trailing_active: bool,
) -> bool:
    """Retorna True se o trailing stop foi atingido."""
    if not trailing_active or trailing_stop_price is None:
        return False
    if side == "LONG":
        return current_price <= trailing_stop_price
    else:
        return current_price >= trailing_stop_price
