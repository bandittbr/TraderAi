"""
Phase 6 — Analytics ORM Models
Tabelas: signal_history, market_regime, strategy_performance_snapshot
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, Integer,
    String, Text, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from app.database import Base


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class MarketRegimeType(str, enum.Enum):
    BULL            = "BULL"
    BEAR            = "BEAR"
    SIDEWAYS        = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    UNKNOWN         = "UNKNOWN"


class SignalOutcome(str, enum.Enum):
    WIN    = "WIN"
    LOSS   = "LOSS"
    OPEN   = "OPEN"    # sinal emitido, ainda não resolvido
    MISSED = "MISSED"  # sinal sem posição correspondente


class SignalDirection(str, enum.Enum):
    BUY     = "BUY"
    SELL    = "SELL"
    NEUTRAL = "NEUTRAL"


# ─────────────────────────────────────────────
# signal_history
# ─────────────────────────────────────────────

class SignalHistory(Base):
    """
    Registra todo sinal gerado pelo Signal Engine,
    com contexto completo no momento da emissão e resultado final.
    """
    __tablename__ = "signal_history"

    id         = Column(Integer, primary_key=True, index=True)
    symbol     = Column(String(20), nullable=False, index=True)
    timeframe  = Column(String(10), nullable=False, default="1h")

    # ── Sinal ──────────────────────────────
    signal     = Column(Enum(SignalDirection), nullable=False)
    confidence = Column(Float, nullable=False)  # 0–100
    regime     = Column(Enum(MarketRegimeType), nullable=False, default=MarketRegimeType.UNKNOWN)

    # ── Contexto técnico no momento do sinal ──
    rsi                = Column(Float, nullable=True)
    ema_alignment      = Column(String(40), nullable=True)   # ex: "9>21>50>200"
    ema_9              = Column(Float, nullable=True)
    ema_21             = Column(Float, nullable=True)
    ema_50             = Column(Float, nullable=True)
    ema_200            = Column(Float, nullable=True)
    macd               = Column(Float, nullable=True)
    macd_signal        = Column(Float, nullable=True)
    macd_histogram     = Column(Float, nullable=True)
    atr                = Column(Float, nullable=True)
    price_at_emission  = Column(Float, nullable=True)

    # ── Critérios atendidos (JSON stringificado) ──
    criteria_met       = Column(Text, nullable=True)   # ex: "rsi_ok,ema_bull,macd_cross"
    criteria_count     = Column(Integer, nullable=True)
    context_boost      = Column(Integer, default=0)

    # ── Contexto de mercado no momento do sinal ──
    news_score         = Column(Float, nullable=True)
    news_sentiment     = Column(String(20), nullable=True)
    fear_greed_value   = Column(Float, nullable=True)
    fear_greed_label   = Column(String(30), nullable=True)
    funding_label      = Column(String(20), nullable=True)
    context_score      = Column(Float, nullable=True)

    # ── Side (BUY→LONG, SELL→SHORT, adicionado via migration) ──
    trade_side         = Column(String(10), nullable=False, default="LONG")  # LONG | SHORT

    # ── Smart Money Context — Phase 7 (adicionado via migration) ──
    had_sweep          = Column(Boolean, nullable=True)
    had_fvg            = Column(Boolean, nullable=True)
    had_hvn            = Column(Boolean, nullable=True)
    had_lvn            = Column(Boolean, nullable=True)
    liquidity_score    = Column(Float,   nullable=True)
    liquidity_label    = Column(String(15), nullable=True)
    sweep_type         = Column(String(30), nullable=True)
    market_structure   = Column(String(20), nullable=True)  # HH+HL, LH+LL, etc.

    # ── Signal Engine V6 — Phase 8 (adicionado via migration) ──
    raw_score       = Column(Float, nullable=True)    # score sem pesos (V5)
    weighted_score  = Column(Float, nullable=True)    # score com pesos adaptativos (V6)
    weights_version = Column(Integer, nullable=True, default=0)

    # ── V7 — Métricas de qualidade do sinal (7.9, 7.11) ──
    module_scores_json  = Column(Text, nullable=True)   # {"technical":83.3,"structural":33.3,"smc":50.0}
    threshold_distance  = Column(Float, nullable=True)  # critérios acima do mínimo do regime
    fee_cost_pct        = Column(Float, nullable=True)  # custo estimado de taxa + slippage (7.11)
    net_pnl_pct         = Column(Float, nullable=True)  # pnl_pct - fee_cost_pct (7.11)

    # ── Resultado (preenchido quando resolvido) ──
    outcome            = Column(Enum(SignalOutcome), nullable=False, default=SignalOutcome.OPEN)
    entry_price        = Column(Float, nullable=True)
    exit_price         = Column(Float, nullable=True)
    pnl_pct            = Column(Float, nullable=True)      # resultado %
    max_favorable_pct  = Column(Float, nullable=True)      # melhor preço favorável %
    max_adverse_pct    = Column(Float, nullable=True)      # pior preço adverso %
    trade_duration_min = Column(Integer, nullable=True)    # duração em minutos
    exit_reason        = Column(String(20), nullable=True) # TP, SL, MANUAL, TIMEOUT

    # ── Timestamps ─────────────────────────
    emitted_at         = Column(DateTime, nullable=False, default=func.now())
    resolved_at        = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SignalHistory {self.symbol} {self.signal} "
            f"{self.confidence:.0f}% @ {self.emitted_at}>"
        )


# ─────────────────────────────────────────────
# market_regime
# ─────────────────────────────────────────────

class MarketRegime(Base):
    """
    Classificação de regime para cada (symbol, timeframe) a cada ciclo.
    Histórico mantido para análise de performance por regime.
    """
    __tablename__ = "market_regime"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(20), nullable=False, index=True)
    timeframe   = Column(String(10), nullable=False, default="1h")
    regime      = Column(Enum(MarketRegimeType), nullable=False)
    confidence  = Column(Float, nullable=False, default=0.0)  # 0–100

    # ── Indicadores usados na classificação ──
    ema_alignment_score = Column(Float, nullable=True)   # +4 = bull perfeito, -4 = bear perfeito
    atr_pct             = Column(Float, nullable=True)   # ATR / price * 100
    price_vs_ema200_pct = Column(Float, nullable=True)   # (price - EMA200) / EMA200 * 100
    ema9_vs_ema21_pct   = Column(Float, nullable=True)   # (EMA9 - EMA21) / EMA21 * 100
    rsi                 = Column(Float, nullable=True)

    # ── Metadata ──
    timestamp   = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<MarketRegime {self.symbol} {self.regime} @ {self.timestamp}>"


# ─────────────────────────────────────────────
# strategy_performance_snapshot
# ─────────────────────────────────────────────

class StrategyPerformanceSnapshot(Base):
    """
    Snapshot computado de métricas de performance para (symbol, regime, período).
    Recalculado periodicamente pelo strategy_analytics.
    """
    __tablename__ = "strategy_performance_snapshot"

    id              = Column(Integer, primary_key=True, index=True)
    symbol          = Column(String(20), nullable=False, index=True)
    regime          = Column(Enum(MarketRegimeType), nullable=True)   # None = todos
    period_days     = Column(Integer, nullable=False, default=30)

    # ── Contagens ──
    total_signals   = Column(Integer, default=0)
    buy_signals     = Column(Integer, default=0)
    sell_signals    = Column(Integer, default=0)
    resolved_signals = Column(Integer, default=0)
    wins            = Column(Integer, default=0)
    losses          = Column(Integer, default=0)

    # ── Métricas agregadas ──
    win_rate        = Column(Float, nullable=True)   # 0–100
    profit_factor   = Column(Float, nullable=True)   # total ganho / total perda
    expectancy      = Column(Float, nullable=True)   # WR*AvgWin - LR*AvgLoss (em %)
    sharpe_ratio    = Column(Float, nullable=True)   # anualizado
    calmar_ratio    = Column(Float, nullable=True)   # retorno anual / max drawdown
    max_drawdown    = Column(Float, nullable=True)   # maior sequência de perdas %
    avg_pnl_pct     = Column(Float, nullable=True)
    avg_win_pct     = Column(Float, nullable=True)
    avg_loss_pct    = Column(Float, nullable=True)
    avg_duration_min = Column(Float, nullable=True)

    # ── Análise de indicadores (JSON) ──
    indicator_win_rates = Column(Text, nullable=True)  # JSON: {rsi_ok: 0.62, macd_cross: 0.58, ...}
    best_combination    = Column(Text, nullable=True)  # JSON: ["rsi_ok", "ema_bull", "macd_cross"]

    computed_at     = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return (
            f"<StrategyPerformanceSnapshot {self.symbol} "
            f"{self.regime} {self.period_days}d @ {self.computed_at}>"
        )
