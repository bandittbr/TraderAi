"""
Worker Agent — Modelos (V7)
Agente 24/7 multi-timeframe com alavancagem adaptativa.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Float, Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WorkerTrade(Base):
    """
    Trade do Worker Agent.
    Suporta alavancagem, múltiplos TP, trailing stop, e fee modeling.
    """
    __tablename__ = "worker_trades"

    id:              Mapped[int]    = mapped_column(Integer, primary_key=True, index=True)
    symbol:          Mapped[str]    = mapped_column(String(20),  nullable=False)
    timeframe_entry: Mapped[str]    = mapped_column(String(4),   default="15m")
    trade_side:      Mapped[str]    = mapped_column(String(6),   nullable=False)  # LONG | SHORT

    # Preços
    entry_price:     Mapped[float] = mapped_column(Float, nullable=False)
    exit_price:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity:        Mapped[float] = mapped_column(Float, nullable=False)
    leverage:        Mapped[int]   = mapped_column(Integer, default=1)  # 1x–3x

    # SL/TP
    stop_loss_price:   Mapped[float] = mapped_column(Float, nullable=False)
    take_profit1_price:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit2_price:Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    take_profit3_price:Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Gestão de posição
    break_even_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    trailing_stop_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trailing_stop_price:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trailing_stop_peak:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    partial_tp1_hit:      Mapped[bool] = mapped_column(Boolean, default=False)
    partial_tp2_hit:      Mapped[bool] = mapped_column(Boolean, default=False)

    # Contexto
    confidence:        Mapped[float] = mapped_column(Float, default=0.0)
    regime_at_entry:   Mapped[str]   = mapped_column(String(20), default="UNKNOWN")
    volatility_at_entry:Mapped[float] = mapped_column(Float, default=0.0)  # ATR% no entry
    direction_score:   Mapped[float] = mapped_column(Float, default=0.0)   # 0–100 score de direção
    entry_reason:      Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Resultado financeiro
    pnl:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # USD bruto
    pnl_pct:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # % bruto
    fee_cost_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # % taxas
    net_pnl_pct:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # % líquido

    # Status
    status:       Mapped[str] = mapped_column(String(10), default="OPEN")   # OPEN | CLOSED
    close_reason: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


class WorkerAccount(Base):
    """Conta do Worker Agent (alavancada ou não)."""
    __tablename__ = "worker_account"

    id:              Mapped[int]    = mapped_column(Integer, primary_key=True)
    balance:         Mapped[float]  = mapped_column(Float, default=10_000.0)
    initial_balance: Mapped[float]  = mapped_column(Float, default=10_000.0)
    peak_balance:    Mapped[float]  = mapped_column(Float, default=10_000.0)
    total_pnl:       Mapped[float]  = mapped_column(Float, default=0.0)
    total_trades:    Mapped[int]    = mapped_column(Integer, default=0)
    winning_trades:  Mapped[int]    = mapped_column(Integer, default=0)
    losing_trades:   Mapped[int]    = mapped_column(Integer, default=0)
    updated_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class WorkerRiskDaily(Base):
    """Risco diário do Worker: PnL, consecutive losses, circuit breaker."""
    __tablename__ = "worker_risk_daily"

    id:                  Mapped[int]    = mapped_column(Integer, primary_key=True)
    date:                Mapped[str]    = mapped_column(String(10), unique=True, nullable=False)
    daily_pnl_usd:       Mapped[float]  = mapped_column(Float, default=0.0)
    daily_pnl_pct:       Mapped[float]  = mapped_column(Float, default=0.0)
    consecutive_losses:  Mapped[int]    = mapped_column(Integer, default=0)
    total_trades:        Mapped[int]    = mapped_column(Integer, default=0)
    winning_trades:      Mapped[int]    = mapped_column(Integer, default=0)
    losing_trades:       Mapped[int]    = mapped_column(Integer, default=0)
    is_blocked:          Mapped[bool]   = mapped_column(Boolean, default=False)
    block_reason:        Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at:          Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
