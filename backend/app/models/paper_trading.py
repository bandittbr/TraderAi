"""
TradeAI - Modelos: Paper Trading (Futures Completo)
Fase 4+: Suporte a LONG e SHORT.

trade_side: LONG (aberto por BUY >= 70%) | SHORT (aberto por SELL >= 70%)
"""

import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.database import Base


class TradeStatus(str, enum.Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"


class TradeSide(str, enum.Enum):
    LONG  = "LONG"
    SHORT = "SHORT"


class PaperAccount(Base):
    """
    Conta virtual de paper trading (futures).
    Saldo atualizado a cada trade fechado.
    PnL SHORT = (entry - exit) * qty  (positivo quando preco cai)
    """

    __tablename__ = "paper_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    balance:         Mapped[float] = mapped_column(Float, nullable=False)
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PaperAccount balance={self.balance:.2f}>"


class PaperTrade(Base):
    """
    Registro de um trade simulado (LONG ou SHORT).

    Abertura:
      LONG  — signal BUY  + confidence >= 70
      SHORT — signal SELL + confidence >= 70

    Fechamento:
      LONG  — SL: price <= entry*(1-SL%)  | TP: price >= entry*(1+TP%)  | SELL signal
      SHORT — SL: price >= entry*(1+SL%)  | TP: price <= entry*(1-TP%)  | BUY signal

    PnL:
      LONG  = (exit - entry) * quantity
      SHORT = (entry - exit) * quantity
    """

    __tablename__ = "paper_trades"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol:     Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe:  Mapped[str] = mapped_column(String(10), nullable=False)

    # Sinal que originou o trade
    signal:     Mapped[str]   = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # LONG ou SHORT — campo principal da Futures upgrade
    trade_side: Mapped[str] = mapped_column(
        SAEnum(TradeSide, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TradeSide.LONG.value,
    )

    # Precos
    entry_price: Mapped[float]        = mapped_column(Float, nullable=False)
    exit_price:  Mapped[float | None] = mapped_column(Float, nullable=True)

    # Tamanho da posicao em unidades do ativo
    quantity: Mapped[float] = mapped_column(Float, nullable=False)

    # Resultado financeiro (preenchido ao fechar)
    pnl:         Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Motivo de fechamento
    close_reason: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # "SIGNAL_CLOSE" | "STOP_LOSS" | "TAKE_PROFIT" | "END_OF_PERIOD"

    status: Mapped[str] = mapped_column(
        SAEnum(TradeStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TradeStatus.OPEN.value,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Phase 12: Trade Management Engine ─────────────────────────────────────

    # Break Even
    break_even_activated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    break_even_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Trailing Stop
    trailing_stop_active: Mapped[Optional[bool]]  = mapped_column(Boolean, nullable=True, default=False)
    trailing_stop_price:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trailing_stop_peak:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Partial TP1
    tp1_hit:           Mapped[Optional[bool]]     = mapped_column(Boolean, nullable=True, default=False)
    tp1_hit_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tp1_partial_qty:   Mapped[Optional[float]]    = mapped_column(Float, nullable=True)
    tp1_partial_price: Mapped[Optional[float]]    = mapped_column(Float, nullable=True)
    remaining_quantity: Mapped[Optional[float]]   = mapped_column(Float, nullable=True)
    partial_pnl:       Mapped[Optional[float]]    = mapped_column(Float, nullable=True)

    # Exit Score at close
    exit_score_at_close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<PaperTrade {self.symbol} {self.trade_side} {self.status} "
            f"entry={self.entry_price} pnl={self.pnl}>"
        )
