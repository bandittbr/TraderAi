"""
Groq Agent — Modelos (V1)
Agente de trading autônomo que usa LLM (Groq API) para decisões.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Float, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GroqTrade(Base):
    """
    Trade do Groq Agent.
    Cada trade é decidido pelo LLM com reasoning registrado.
    """
    __tablename__ = "groq_trades"

    id:              Mapped[int]    = mapped_column(Integer, primary_key=True, index=True)
    symbol:          Mapped[str]    = mapped_column(String(20),  nullable=False)
    trade_side:      Mapped[str]    = mapped_column(String(6),   nullable=False)  # LONG | SHORT

    # Preços
    entry_price:     Mapped[float] = mapped_column(Float, nullable=False)
    exit_price:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity:        Mapped[float] = mapped_column(Float, nullable=False)
    leverage:        Mapped[float] = mapped_column(Float, default=10.0)  # Alavancagem aplicada

    # SL/TP decididos pelo LLM
    stop_loss_price:   Mapped[float] = mapped_column(Float, nullable=False)
    take_profit_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Contexto da decisão
    confidence:        Mapped[float] = mapped_column(Float, default=0.0)
    regime_at_entry:   Mapped[str]   = mapped_column(String(20), default="UNKNOWN")

    # Resultado financeiro
    pnl:          Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # USD
    pnl_pct:      Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # %
    fee_cost_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)    # %
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


class GroqAccount(Base):
    """Conta do Groq Agent — começa com $10,000 virtuais."""
    __tablename__ = "groq_account"

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


class GroqThinking(Base):
    """
    Log de raciocínio do LLM a cada ciclo.
    Armazena o prompt enviado, a resposta, e o reasoning.
    """
    __tablename__ = "groq_thinking"

    id:           Mapped[int]    = mapped_column(Integer, primary_key=True, index=True)
    symbol:       Mapped[str]    = mapped_column(String(20), nullable=False)
    action:       Mapped[str]    = mapped_column(String(10), nullable=False)  # BUY | SELL | HOLD
    confidence:   Mapped[float]  = mapped_column(Float, default=0.0)
    reasoning:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # Pensamento do LLM
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON bruto
    prompt_tokens:Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens:Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used:   Mapped[str]    = mapped_column(String(50), default="llama-3.3-70b-versatile")
    latency_ms:   Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error:        Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at:   Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class GroqRiskDaily(Base):
    """Risco diário do Groq Agent."""
    __tablename__ = "groq_risk_daily"

    id:                  Mapped[int]    = mapped_column(Integer, primary_key=True)
    date:                Mapped[str]    = mapped_column(String(10), unique=True, nullable=False)
    daily_pnl_usd:       Mapped[float]  = mapped_column(Float, default=0.0)
    daily_pnl_pct:       Mapped[float]  = mapped_column(Float, default=0.0)
    consecutive_losses:  Mapped[int]    = mapped_column(Integer, default=0)
    total_trades:        Mapped[int]    = mapped_column(Integer, default=0)
    winning_trades:      Mapped[int]    = mapped_column(Integer, default=0)
    losing_trades:       Mapped[int]    = mapped_column(Integer, default=0)
    is_blocked:          Mapped[bool]   = mapped_column(Boolean, default=False)
    updated_at:          Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
