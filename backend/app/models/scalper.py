"""
TradeAI — Scalper Engine ORM Models (Fase 13)
Módulo completamente independente do Paper Trading.
"""
import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, Integer, Date, Text, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ScalperTradeStatus(str, enum.Enum):
    OPEN   = "OPEN"
    CLOSED = "CLOSED"


class ScalperTradeSide(str, enum.Enum):
    LONG  = "LONG"
    SHORT = "SHORT"


class ScalperCloseReason(str, enum.Enum):
    STOP_LOSS       = "STOP_LOSS"
    TAKE_PROFIT     = "TAKE_PROFIT"
    TRAILING_STOP   = "TRAILING_STOP"
    BREAK_EVEN_STOP = "BREAK_EVEN_STOP"
    SIGNAL_CLOSE    = "SIGNAL_CLOSE"
    TIME_STOP       = "TIME_STOP"
    MANUAL          = "MANUAL"


# ── Conta do Scalper (saldo isolado) ─────────────────────────────────────────
class ScalperAccount(Base):
    __tablename__ = "scalper_account"

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True)
    balance:         Mapped[float] = mapped_column(Float, default=10_000.0)
    initial_balance: Mapped[float] = mapped_column(Float, default=10_000.0)
    peak_balance:    Mapped[float] = mapped_column(Float, default=10_000.0)
    total_pnl:       Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ── Trades do Scalper ─────────────────────────────────────────────────────────
class ScalperTrade(Base):
    __tablename__ = "scalper_trades"

    id:               Mapped[int]   = mapped_column(Integer, primary_key=True)
    symbol:           Mapped[str]   = mapped_column(String(20), nullable=False)
    timeframe_entry:  Mapped[str]   = mapped_column(String(4),  default="1m")
    trade_side:       Mapped[str]   = mapped_column(String(6),  nullable=False)
    trend_15m:        Mapped[str]   = mapped_column(String(10), default="UNKNOWN")
    confirm_5m:       Mapped[bool]  = mapped_column(Boolean, default=False)
    confidence:       Mapped[float] = mapped_column(Float,   default=0.0)

    entry_price:      Mapped[float] = mapped_column(Float, nullable=False)
    exit_price:       Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity:         Mapped[float] = mapped_column(Float, nullable=False)
    risk_usd:         Mapped[float] = mapped_column(Float, default=10.0)

    stop_loss_price:    Mapped[float] = mapped_column(Float, nullable=False)
    take_profit_price:  Mapped[float] = mapped_column(Float, nullable=False)
    break_even_price:   Mapped[float | None] = mapped_column(Float, nullable=True)

    break_even_activated: Mapped[bool]         = mapped_column(Boolean, default=False)
    trailing_stop_active: Mapped[bool]         = mapped_column(Boolean, default=False)
    trailing_stop_price:  Mapped[float | None] = mapped_column(Float, nullable=True)
    trailing_stop_peak:   Mapped[float | None] = mapped_column(Float, nullable=True)

    pnl:         Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_pct:     Mapped[float | None] = mapped_column(Float, nullable=True)
    status:      Mapped[str]          = mapped_column(String(10), default="OPEN")
    close_reason: Mapped[str | None]  = mapped_column(String(30), nullable=True)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)


# ── Risco Diário ─────────────────────────────────────────────────────────────
class ScalperRiskDaily(Base):
    __tablename__ = "scalper_risk_daily"

    id:                  Mapped[int]   = mapped_column(Integer, primary_key=True)
    date:                Mapped[str]   = mapped_column(String(10), unique=True, nullable=False)
    daily_pnl_usd:       Mapped[float] = mapped_column(Float, default=0.0)
    daily_pnl_pct:       Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_losses:  Mapped[int]   = mapped_column(Integer, default=0)
    total_trades:        Mapped[int]   = mapped_column(Integer, default=0)
    winning_trades:      Mapped[int]   = mapped_column(Integer, default=0)
    losing_trades:       Mapped[int]   = mapped_column(Integer, default=0)
    is_blocked:          Mapped[bool]  = mapped_column(Boolean, default=False)
    block_reason:        Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ── Histórico de Sinais do Scalper ────────────────────────────────────────────
class ScalperSignal(Base):
    __tablename__ = "scalper_signals"

    id:           Mapped[int]   = mapped_column(Integer, primary_key=True)
    symbol:       Mapped[str]   = mapped_column(String(20), nullable=False)
    direction:    Mapped[str]   = mapped_column(String(6),  nullable=False)   # LONG/SHORT/NONE
    trend_15m:    Mapped[str]   = mapped_column(String(10), default="UNKNOWN")
    confirm_5m:   Mapped[bool]  = mapped_column(Boolean, default=False)
    entry_1m:     Mapped[bool]  = mapped_column(Boolean, default=False)
    confidence:   Mapped[float] = mapped_column(Float, default=0.0)
    price:        Mapped[float] = mapped_column(Float, nullable=False)
    rsi_1m:       Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi_5m:       Mapped[float | None] = mapped_column(Float, nullable=True)
    ema9_15m:     Mapped[float | None] = mapped_column(Float, nullable=True)
    ema21_15m:    Mapped[float | None] = mapped_column(Float, nullable=True)
    acted_on:     Mapped[bool]  = mapped_column(Boolean, default=False)
    reject_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    emitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
