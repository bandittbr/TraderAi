"""
TradeAI - Fear & Greed Index (Fase 5)
Fonte: alternative.me (API pública gratuita, sem autenticação)
URL:   https://api.alternative.me/fng/?limit=1

Classificação:
  0-24   → Extreme Fear
  25-44  → Fear
  45-55  → Neutral
  56-75  → Greed
  76-100 → Extreme Greed
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.market_context import FearGreedIndex
from app.logger import get_logger

logger = get_logger(__name__)

FNG_URL     = "https://api.alternative.me/fng/?limit=1"
TIMEOUT_SEC = 10


def classify(value: int) -> str:
    if value <= 24: return "Extreme Fear"
    if value <= 44: return "Fear"
    if value <= 55: return "Neutral"
    if value <= 75: return "Greed"
    return "Extreme Greed"


class FearGreedService:

    async def fetch_and_save(self) -> FearGreedIndex | None:
        """Busca o índice atual e persiste no banco."""
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
                resp = await client.get(FNG_URL)
                resp.raise_for_status()
                data = resp.json()

            entry = data["data"][0]
            value     = int(entry["value"])
            label     = entry.get("value_classification", classify(value))
            timestamp = int(entry.get("timestamp", datetime.now(timezone.utc).timestamp()))

            async with AsyncSessionLocal() as session:
                # Verifica se já temos esse timestamp
                result = await session.execute(
                    select(FearGreedIndex)
                    .where(FearGreedIndex.timestamp == timestamp)
                    .limit(1)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    return existing

                fg = FearGreedIndex(
                    value          = value,
                    classification = label,
                    timestamp      = timestamp,
                )
                session.add(fg)
                await session.commit()
                await session.refresh(fg)

            logger.info(f"[fear_greed] {value} — {label}")
            return fg

        except Exception as exc:
            logger.warning(f"[fear_greed] Falha: {exc}")
            return None

    async def get_latest(self) -> FearGreedIndex | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FearGreedIndex)
                .order_by(FearGreedIndex.timestamp.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_history(self, limit: int = 30) -> list[FearGreedIndex]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FearGreedIndex)
                .order_by(FearGreedIndex.timestamp.desc())
                .limit(limit)
            )
            return list(result.scalars().all())


fear_greed_service = FearGreedService()
