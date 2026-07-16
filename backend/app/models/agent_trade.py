"""
Multi-Agent Trading System — Modelo de banco de dados
Cada agente tem sua própria conta e trades.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Float, Integer, String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentAccount(Base):
    """
    Conta de um agente de trading.
    Cada agente tem $100.000 de capital inicial simulado.
    """
    __tablename__ = "agent_accounts"

    id:              Mapped[int]    = mapped_column(Integer, primary_key=True)
    agent_name:      Mapped[str]    = mapped_column(String(50), unique=True, nullable=False, index=True)
    balance:         Mapped[float]  = mapped_column(Float, default=100_000.0)
    initial_balance: Mapped[float]  = mapped_column(Float, default=100_000.0)
    peak_balance:    Mapped[float]  = mapped_column(Float, default=100_000.0)
    total_pnl:       Mapped[float]  = mapped_column(Float, default=0.0)
    total_trades:    Mapped[int]    = mapped_column(Integer, default=0)
    winning_trades:  Mapped[int]    = mapped_column(Integer, default=0)
    losing_trades:   Mapped[int]    = mapped_column(Integer, default=0)
    enabled:         Mapped[bool]   = mapped_column(Boolean, default=True)
    created_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at:      Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class AgentTrade(Base):
    """
    Trade de um agente de trading.
    """
    __tablename__ = "agent_trades"

    id:              Mapped[int]    = mapped_column(Integer, primary_key=True, index=True)
    agent_name:      Mapped[str]    = mapped_column(String(50), nullable=False, index=True)
    symbol:          Mapped[str]    = mapped_column(String(20), nullable=False)
    timeframe_entry: Mapped[str]    = mapped_column(String(4), default="1h")
    trade_side:      Mapped[str]    = mapped_column(String(6), nullable=False)  # LONG | SHORT

    # Preços
    entry_price:     Mapped[float] = mapped_column(Float, nullable=False)
    exit_price:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity:        Mapped[float] = mapped_column(Float, nullable=False)
    leverage:        Mapped[int]   = mapped_column(Integer, default=1)

    # SL/TP
    stop_loss_price:   Mapped[float] = mapped_column(Float, nullable=False)
    take_profit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    volatility_at_entry:Mapped[float] = mapped_column(Float, default=0.0)
    entry_reason:      Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Resultado financeiro
    pnl:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_pct:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fee_cost_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    net_pnl_pct:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    status:       Mapped[str] = mapped_column(String(10), default="OPEN")
    close_reason: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
