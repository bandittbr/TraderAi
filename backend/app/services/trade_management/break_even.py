"""
TradeAI — Break Even Engine (Fase 12)

Quando o trade atinge o trigger de lucro configurado,
o stop loss é movido para o preço de entrada (break-even).
Determinístico e auditável.
"""

from __future__ import annotations

from app.config import settings


def should_activate(
    side: str,
    entry_price: float,
    current_price: float,
    already_activated: bool = False,
) -> bool:
    """
    Retorna True se o break-even deve ser ativado agora.
    Trigger: lucro >= paper_break_even_trigger_pct
    """
    if already_activated:
        return False

    trigger = settings.paper_break_even_trigger_pct / 100

    if side == "LONG":
        return current_price >= entry_price * (1 + trigger)
    else:  # SHORT
        return current_price <= entry_price * (1 - trigger)


def get_break_even_stop(side: str, entry_price: float) -> float:
    """Retorna o nível de stop após ativação do break-even (= entry_price)."""
    return entry_price


def check_stop_hit(
    side: str,
    entry_price: float,
    current_price: float,
    be_activated: bool,
) -> bool:
    """
    Retorna True se o break-even stop foi atingido.
    Só aplicável se break-even já estiver ativo.
    """
    if not be_activated:
        return False
    if side == "LONG":
        return current_price <= entry_price
    else:
        return current_price >= entry_price
