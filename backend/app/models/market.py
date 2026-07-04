"""
TradeAI - Modelos: Dados de Mercado
Tabelas para armazenar candles históricos e estatísticas 24h por ativo.
Fase 2: market_candles + market_stats.
Fase 3+: adicionar orders, portfolio, trades.
"""

from sqlalchemy import String, Float, Integer, BigInteger, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from app.database import Base


class MarketCandle(Base):
    """
    Armazena candles OHLCV por símbolo e timeframe.
    Chave única: (symbol, timeframe, timestamp) — evita duplicatas.
    """

    __tablename__ = "market_candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)

    # Timestamp em segundos Unix (epoch seconds — compatível com lightweight-charts)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # OHLCV
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)

    # Restrições e índices para performance
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_candle"),
        Index("ix_candle_lookup", "symbol", "timeframe", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketCandle {self.symbol} {self.timeframe} "
            f"ts={self.timestamp} c={self.close}>"
        )


class MarketStat(Base):
    """
    Armazena estatísticas 24h por símbolo.
    Uma linha por símbolo — atualizada via upsert.
    Fase 2: dados vindos da Binance REST API.
    Fase 3+: adicionar funding_rate, open_interest, sentiment_score.
    """

    __tablename__ = "market_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Preço e variação
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    change_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # percentual

    # Volume e range 24h
    volume_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    high_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    low_24h: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Controle de atualização
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MarketStat {self.symbol} price={self.price} chg={self.change_24h}%>"
