"""
TradeAI - Funding Rate Service (Fase 5)
Fonte: Binance Futures API pública (sem autenticação)
URL:   GET https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1

Classificação:
  rate > +0.01%  → BULLISH  (longs pagam shorts; mercado sobrecomprado, mas otimista)
  rate < -0.01%  → BEARISH  (shorts pagam longs; mercado pessimista)
  else           → NEUTRAL
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.market_context import FundingRate as FundingRateModel
from app.logger import get_logger

logger = get_logger(__name__)

FAPI_BASE   = "https://fapi.binance.com"
TIMEOUT_SEC = 10
SYMBOLS     = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

BULLISH_THRESHOLD =  0.0001   # +0.01%
BEARISH_THRESHOLD = -0.0001   # -0.01%


def classify_funding(rate: float) -> str:
    if rate > BULLISH_THRESHOLD:  return "BULLISH"
    if rate < BEARISH_THRESHOLD:  return "BEARISH"
    return "NEUTRAL"


class FundingRateService:

    async def fetch_and_save_all(self) -> list[FundingRateModel]:
        """Busca funding rate atual para todos os símbolos."""
        results = []
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            for symbol in SYMBOLS:
                fr = await self._fetch_symbol(client, symbol)
                if fr:
                    results.append(fr)
        return results

    async def _fetch_symbol(
        self, client: httpx.AsyncClient, symbol: str
    ) -> FundingRateModel | None:
        try:
            resp = await client.get(
                f"{FAPI_BASE}/fapi/v1/fundingRate",
                params={"symbol": symbol, "limit": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            if not data:
                return None

            entry     = data[0]
            rate      = float(entry["fundingRate"])
            timestamp = int(entry["fundingTime"]) // 1000   # ms → s

            async with AsyncSessionLocal() as session:
                existing = await session.execute(
                    select(FundingRateModel).where(
                        FundingRateModel.symbol    == symbol,
                        FundingRateModel.timestamp == timestamp,
                    ).limit(1)
                )
                if existing.scalar_one_or_none():
                    return await self.get_latest(symbol)

                fr = FundingRateModel(
                    symbol       = symbol,
                    rate         = rate,
                    rate_percent = round(rate * 100, 6),
                    sentiment    = classify_funding(rate),
                    timestamp    = timestamp,
                )
                session.add(fr)
                await session.commit()
                await session.refresh(fr)

            logger.debug(f"[funding] {symbol}: {rate*100:.4f}% ({fr.sentiment})")
            return fr

        except Exception as exc:
            logger.warning(f"[funding] Falha {symbol}: {exc}")
            return None

    async def get_latest(self, symbol: str) -> FundingRateModel | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FundingRateModel)
                .where(FundingRateModel.symbol == symbol)
                .order_by(FundingRateModel.timestamp.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_all_latest(self) -> list[FundingRateModel]:
        results = []
        for symbol in SYMBOLS:
            fr = await self.get_latest(symbol)
            if fr:
                results.append(fr)
        return results


funding_rate_service = FundingRateService()
