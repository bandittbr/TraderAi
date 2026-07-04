"""
TradeAI — Time Stop Engine (Fase 12)

Fecha trades que ultrapassaram o limite temporal configurado.
Determinístico: baseado exclusivamente em datetime arithmetic.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import settings


def check_time_stop(opened_at: datetime, now: datetime | None = None) -> bool:
    """
    Retorna True se o trade ultrapassou paper_max_hours_open.
    opened_at pode ser tz-aware ou tz-naive (será tratado como UTC).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Normaliza timezone
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    hours_open = (now - opened_at).total_seconds() / 3600
    return hours_open >= settings.paper_max_hours_open


def hours_open(opened_at: datetime, now: datetime | None = None) -> float:
    """Retorna quantas horas o trade está aberto."""
    if now is None:
        now = datetime.now(timezone.utc)
    if opened_at.tzinfo is None:
        opened_at = opened_at.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return round((now - opened_at).total_seconds() / 3600, 3)
