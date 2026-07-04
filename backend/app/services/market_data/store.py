"""
TradeAI - MarketDataStore
Camada de persistência exclusiva para dados de mercado.
Isola toda a lógica de banco de dados dos serviços e endpoints.

Fase 2: upsert de candles e stats.
Fase 3+: adicionar bulk insert otimizado, particionamento por data, TTL de limpeza.
"""

from datetime import datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.market import MarketCandle, MarketStat
from app.logger import get_logger

logger = get_logger(__name__)


class MarketDataStore:
    """Operações de leitura e escrita de dados de mercado no SQLite."""

    # ── Candles ───────────────────────────────────────────────────────────────

    async def save_candles(
        self,
        symbol: str,
        timeframe: str,
        raw_candles: list[list],
    ) -> int:
        """
        Salva/atualiza candles no banco (upsert por symbol+timeframe+timestamp).
        Os candles vêm no formato Binance: [open_time_ms, o, h, l, c, v, ...]
        Retorna o número de registros novos inseridos.
        """
        if not raw_candles:
            return 0

        inserted = 0
        async with AsyncSessionLocal() as session:
            for row in raw_candles:
                # Converte milissegundos para segundos (padrão lightweight-charts)
                ts = int(row[0]) // 1000

                result = await session.execute(
                    select(MarketCandle).where(
                        MarketCandle.symbol == symbol,
                        MarketCandle.timeframe == timeframe,
                        MarketCandle.timestamp == ts,
                    )
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Atualiza candle em andamento (close, high, low, volume mudam)
                    existing.open   = float(row[1])
                    existing.high   = float(row[2])
                    existing.low    = float(row[3])
                    existing.close  = float(row[4])
                    existing.volume = float(row[5])
                else:
                    session.add(MarketCandle(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=ts,
                        open=float(row[1]),
                        high=float(row[2]),
                        low=float(row[3]),
                        close=float(row[4]),
                        volume=float(row[5]),
                    ))
                    inserted += 1

            await session.commit()

        return inserted

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[MarketCandle]:
        """
        Retorna os candles mais recentes do banco, ordenados do mais antigo para o mais novo.
        Ordem crescente de timestamp é exigida pelo lightweight-charts.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketCandle)
                .where(
                    MarketCandle.symbol == symbol,
                    MarketCandle.timeframe == timeframe,
                )
                .order_by(MarketCandle.timestamp.desc())
                .limit(limit)
            )
            candles = result.scalars().all()
            # Inverte para ordem cronológica crescente
            return list(reversed(candles))

    async def count_candles(self, symbol: str, timeframe: str) -> int:
        """Conta candles disponíveis para um par símbolo/timeframe."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketCandle).where(
                    MarketCandle.symbol == symbol,
                    MarketCandle.timeframe == timeframe,
                )
            )
            return len(result.scalars().all())

    # ── Estatísticas 24h ──────────────────────────────────────────────────────

    async def save_stats(self, symbol: str, ticker: dict) -> None:
        """
        Salva/atualiza estatísticas 24h para um símbolo.
        Uma linha por símbolo na tabela market_stats.
        """
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketStat).where(MarketStat.symbol == symbol)
            )
            stat = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)
            values = {
                "symbol":     symbol,
                "price":      float(ticker.get("lastPrice", 0)),
                "change_24h": float(ticker.get("priceChangePercent", 0)),
                "volume_24h": float(ticker.get("volume", 0)),
                "high_24h":   float(ticker.get("highPrice", 0)),
                "low_24h":    float(ticker.get("lowPrice", 0)),
                "updated_at": now,
            }

            if stat:
                for key, val in values.items():
                    setattr(stat, key, val)
            else:
                session.add(MarketStat(**values))

            await session.commit()

    async def get_stats(self, symbol: str) -> MarketStat | None:
        """Retorna as estatísticas 24h armazenadas para um símbolo."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketStat).where(MarketStat.symbol == symbol)
            )
            return result.scalar_one_or_none()

    async def get_all_stats(self) -> list[MarketStat]:
        """Retorna estatísticas 24h de todos os símbolos cadastrados."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(MarketStat))
            return list(result.scalars().all())


# Instância singleton
store = MarketDataStore()
