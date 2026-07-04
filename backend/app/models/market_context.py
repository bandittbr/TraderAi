"""
TradeAI - Modelos: Contexto de Mercado (Fase 5)
Tabelas para notícias, Fear & Greed, Open Interest e Funding Rate.
"""

from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, BigInteger, DateTime, Text, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MarketNews(Base):
    """
    Notícias de mercado coletadas de fontes RSS públicas.
    Sentimento e impacto calculados por regras sem IA.
    """
    __tablename__ = "market_news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    source:       Mapped[str]   = mapped_column(String(50), nullable=False)
    title:        Mapped[str]   = mapped_column(String(500), nullable=False)
    summary:      Mapped[str | None] = mapped_column(Text, nullable=True)
    url:          Mapped[str]   = mapped_column(String(1000), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Classificação
    asset:      Mapped[str]   = mapped_column(String(20), nullable=False, default="GENERAL")
    # BTC | ETH | SOL | GENERAL | CRYPTO
    category:   Mapped[str]   = mapped_column(String(30), nullable=False, default="NEWS")
    # REGULATION | ADOPTION | TECH | SECURITY | MACRO | NEWS

    # Análise de sentimento (rule-based)
    sentiment:    Mapped[str]   = mapped_column(String(10), nullable=False, default="NEUTRAL")
    # POSITIVE | NEUTRAL | NEGATIVE
    impact_score: Mapped[float] = mapped_column(Float, nullable=False, default=50.0)
    # 0-100

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("url", name="uq_news_url"),
        Index("ix_news_asset_published", "asset", "published_at"),
        Index("ix_news_published", "published_at"),
    )

    def __repr__(self) -> str:
        return f"<MarketNews [{self.asset}] {self.title[:50]}>"


class FearGreedIndex(Base):
    """
    Índice Fear & Greed do mercado cripto (fonte: alternative.me).
    Atualizado a cada hora.
    """
    __tablename__ = "fear_greed_index"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    value:          Mapped[int]  = mapped_column(Integer, nullable=False)   # 0-100
    classification: Mapped[str]  = mapped_column(String(30), nullable=False)
    # Extreme Fear | Fear | Neutral | Greed | Extreme Greed
    timestamp:  Mapped[int]  = mapped_column(BigInteger, nullable=False)   # epoch seconds

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_fg_timestamp"),
        Index("ix_fg_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<FearGreed {self.value} {self.classification}>"


class OpenInterest(Base):
    """
    Open Interest de contratos futuros perpétuos (Binance Futures).
    Representa o total de contratos abertos — indica força da tendência.
    """
    __tablename__ = "open_interest"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol:          Mapped[str]   = mapped_column(String(20), nullable=False)
    open_interest:   Mapped[float] = mapped_column(Float, nullable=False)   # em contratos
    open_interest_usd: Mapped[float] = mapped_column(Float, nullable=False) # em USD
    timestamp:       Mapped[int]   = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uq_oi_symbol_ts"),
        Index("ix_oi_symbol_ts", "symbol", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<OpenInterest {self.symbol} {self.open_interest_usd:.0f}>"


class FundingRate(Base):
    """
    Funding Rate de contratos perpétuos (Binance Futures).
    Positivo → longs pagam shorts (mercado bullish).
    Negativo → shorts pagam longs (mercado bearish).
    """
    __tablename__ = "funding_rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol:       Mapped[str]   = mapped_column(String(20), nullable=False)
    rate:         Mapped[float] = mapped_column(Float, nullable=False)   # ex: 0.0001 = 0.01%
    rate_percent: Mapped[float] = mapped_column(Float, nullable=False)   # rate * 100
    sentiment:    Mapped[str]   = mapped_column(String(10), nullable=False)
    # BULLISH | NEUTRAL | BEARISH
    timestamp:    Mapped[int]   = mapped_column(BigInteger, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uq_fr_symbol_ts"),
        Index("ix_fr_symbol_ts", "symbol", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<FundingRate {self.symbol} {self.rate_percent:.4f}% {self.sentiment}>"
