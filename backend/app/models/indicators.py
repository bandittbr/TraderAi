"""
TradeAI - Modelo: Indicadores Técnicos (Fase 3)
Armazena RSI, EMAs, MACD e ATR calculados por símbolo e timeframe.
"""

from sqlalchemy import String, Float, Integer, BigInteger, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, timezone
from typing import Optional
from app.database import Base


class MarketIndicator(Base):
    """
    Indicadores técnicos calculados a partir dos candles.
    Uma linha por (symbol, timeframe, timestamp) — atualizada via upsert.
    Fase 4+: adicionar funding_rate_score, sentiment_score, ai_signal.
    """

    __tablename__ = "market_indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Identificação
    symbol:    Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp: Mapped[int] = mapped_column(BigInteger, nullable=False)  # epoch seconds

    # RSI
    rsi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Médias móveis exponenciais
    ema_9:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ema_21:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ema_50:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ema_200: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # MACD
    macd:           Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_signal:    Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ATR
    atr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Controle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_indicator"),
        Index("ix_indicator_lookup", "symbol", "timeframe", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketIndicator {self.symbol} {self.timeframe} "
            f"ts={self.timestamp} rsi={self.rsi:.1f}>"
            if self.rsi else f"<MarketIndicator {self.symbol} {self.timeframe}>"
        )
