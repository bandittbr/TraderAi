"""
TradeAI - Open Interest Service (Fase 5)
Fonte: Binance Futures API pública (sem autenticação)
URL:   GET https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT

Open Interest crescente + preço subindo → forte tendência bullish
Open Interest crescente + preço caindo → forte tendência bearish
Open Interest decrescente               → tendência enfraquecendo
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.market_context import OpenInterest as OIModel
from app.logger import get_logger

logger = get_logger(__name__)

FAPI_BASE   = "https://fapi.binance.com"
TIMEOUT_SEC = 10
SYMBOLS     = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


class OpenInterestService:

    async def fetch_and_save_all(self) -> list[OIModel]:
        results = []
        async with httpx.AsyncClient(timeout=TIMEOUT_SEC) as client:
            for symbol in SYMBOLS:
                oi = await self._fetch_symbol(client, symbol)
                if oi:
                    results.append(oi)
        return results

    async def _fetch_symbol(
        self, client: httpx.AsyncClient, symbol: str
    ) -> OIModel | None:
        try:
            # Open Interest atual
            resp = await client.get(
                f"{FAPI_BASE}/fapi/v1/openInterest",
                params={"symbol": symbol},
            )
            resp.raise_for_status()
            data = resp.json()

            oi_contracts = float(data["openInterest"])
            timestamp    = int(data["time"]) // 1000   # ms → s

            # Obtém preço atual para calcular OI em USD
            price_resp = await client.get(
                f"{FAPI_BASE}/fapi/v1/ticker/price",
                params={"symbol": symbol},
            )
            price = float(price_resp.json()["price"]) if price_resp.status_code == 200 else 1.0
            oi_usd = oi_contracts * price

            async with AsyncSessionLocal() as session:
                existing = await session.execute(
                    select(OIModel).where(
                        OIModel.symbol    == symbol,
                        OIModel.timestamp == timestamp,
                    ).limit(1)
                )
                if existing.scalar_one_or_none():
                    return await self.get_latest(symbol)

                oi = OIModel(
                    symbol            = symbol,
                    open_interest     = oi_contracts,
                    open_interest_usd = oi_usd,
                    timestamp         = timestamp,
                )
                session.add(oi)
                await session.commit()
                await session.refresh(oi)

            logger.debug(f"[oi] {symbol}: ${oi_usd/1e9:.2f}B")
            return oi

        except Exception as exc:
            logger.warning(f"[oi] Falha {symbol}: {exc}")
            return None

    async def get_latest(self, symbol: str) -> OIModel | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OIModel)
                .where(OIModel.symbol == symbol)
                .order_by(OIModel.timestamp.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def get_history(self, symbol: str, limit: int = 24) -> list[OIModel]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(OIModel)
                .where(OIModel.symbol == symbol)
                .order_by(OIModel.timestamp.desc())
                .limit(limit)
            )
            return list(reversed(result.scalars().all()))

    async def get_oi_change_pct(self, symbol: str) -> float | None:
        """Variação percentual do OI nas últimas 2 leituras."""
        history = await self.get_history(symbol, limit=2)
        if len(history) < 2:
            return None
        prev, curr = history[0], history[1]
        if prev.open_interest_usd == 0:
            return None
        return ((curr.open_interest_usd - prev.open_interest_usd)
                / prev.open_interest_usd) * 100

    async def get_all_latest(self) -> list[OIModel]:
        results = []
        for symbol in SYMBOLS:
            oi = await self.get_latest(symbol)
            if oi:
                results.append(oi)
        return results


open_interest_service = OpenInterestService()
