"""
TradeAI — Partial Take Profit Engine (Fase 12)

TP1 (paper_tp1_pct):  fecha 50% da posição, mantém o restante.
TP2 (paper_take_profit_percent): fecha a posição restante.

Determinístico — baseado apenas em preço e configuração.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.config import settings


PARTIAL_EXIT_RATIO = 0.5   # 50% da posição no TP1


@dataclass
class PartialTPResult:
    tp1_triggered: bool
    tp2_triggered: bool
    partial_qty:   Optional[float]  # qty fechada no TP1
    remaining_qty: Optional[float]  # qty restante após TP1


def check(
    side: str,
    entry_price: float,
    current_price: float,
    original_quantity: float,
    tp1_already_hit: bool,
) -> PartialTPResult:
    """
    Verifica se TP1 ou TP2 foram atingidos.
    """
    tp1_pct = settings.paper_tp1_pct / 100
    tp2_pct = settings.paper_take_profit_percent / 100

    if side == "LONG":
        profit_pct = (current_price - entry_price) / entry_price
        tp1_hit = profit_pct >= tp1_pct
        tp2_hit = profit_pct >= tp2_pct
    else:  # SHORT
        profit_pct = (entry_price - current_price) / entry_price
        tp1_hit = profit_pct >= tp1_pct
        tp2_hit = profit_pct >= tp2_pct

    # TP1 só dispara uma vez
    if tp1_hit and not tp1_already_hit:
        partial_qty   = round(original_quantity * PARTIAL_EXIT_RATIO, 8)
        remaining_qty = round(original_quantity - partial_qty, 8)
        return PartialTPResult(
            tp1_triggered=True,
            tp2_triggered=False,
            partial_qty=partial_qty,
            remaining_qty=remaining_qty,
        )

    # TP2 (fecha o restante)
    if tp2_hit:
        # Se TP1 já foi atingido, a qty restante é menor
        return PartialTPResult(
            tp1_triggered=False,
            tp2_triggered=True,
            partial_qty=None,
            remaining_qty=None,
        )

    return PartialTPResult(
        tp1_triggered=False, tp2_triggered=False,
        partial_qty=None, remaining_qty=None,
    )


def calc_partial_pnl(
    side: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
) -> float:
    """Calcula PnL de uma saída parcial."""
    if side == "LONG":
        return round((exit_price - entry_price) * quantity, 8)
    else:
        return round((entry_price - exit_price) * quantity, 8)
