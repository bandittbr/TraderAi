"""
Fase 9 — Alpha Discovery Engine ORM Models
Tabelas: alpha_patterns, alpha_pattern_stats, setup_quality_history
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, Boolean, func

from app.database import Base


class AlphaPattern(Base):
    """
    Padrão identificado automaticamente no histórico de sinais.
    Um padrão é uma combinação de 1–3 critérios com estatísticas calculadas.
    """
    __tablename__ = "alpha_patterns"

    id              = Column(Integer, primary_key=True, index=True)
    pattern_key     = Column(String(200), nullable=False, unique=True, index=True)
    # Ex: "bos_bullish|bullish_fvg" ou "rsi_ok|ema_bull|macd_positive"
    criteria        = Column(Text, nullable=False)   # JSON list de critérios
    criteria_count  = Column(Integer, nullable=False, default=1)

    # Contexto do padrão
    symbol          = Column(String(20), nullable=True)   # None = global
    regime          = Column(String(20), nullable=True)   # None = todos
    trade_side      = Column(String(10), nullable=True)   # LONG | SHORT | None

    # Métricas de performance
    sample_size     = Column(Integer, nullable=False, default=0)
    resolved        = Column(Integer, nullable=False, default=0)
    wins            = Column(Integer, nullable=False, default=0)
    losses          = Column(Integer, nullable=False, default=0)
    win_rate        = Column(Float, nullable=True)       # 0–100
    profit_factor   = Column(Float, nullable=True)
    expectancy      = Column(Float, nullable=True)       # média pnl_pct
    sharpe          = Column(Float, nullable=True)
    max_drawdown    = Column(Float, nullable=True)
    avg_win_pct     = Column(Float, nullable=True)
    avg_loss_pct    = Column(Float, nullable=True)

    # Score composto (WR * PF normalizado)
    alpha_score     = Column(Float, nullable=True)       # 0–100
    is_positive     = Column(Boolean, nullable=False, default=True)  # True = alpha positivo
    sufficient_data = Column(Boolean, nullable=False, default=False)

    # Timestamps
    first_seen      = Column(DateTime, nullable=False, default=func.now())
    last_updated    = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AlphaPattern {self.pattern_key} WR={self.win_rate:.1f}% PF={self.profit_factor:.2f}>"


class AlphaPatternStats(Base):
    """
    Snapshot histórico de stats por padrão — permite rastrear evolução.
    Gerado a cada ciclo de análise alpha.
    """
    __tablename__ = "alpha_pattern_stats"

    id              = Column(Integer, primary_key=True, index=True)
    pattern_key     = Column(String(200), nullable=False, index=True)
    symbol          = Column(String(20), nullable=True)

    # Métricas no momento do snapshot
    sample_size     = Column(Integer, nullable=False, default=0)
    win_rate        = Column(Float, nullable=True)
    profit_factor   = Column(Float, nullable=True)
    expectancy      = Column(Float, nullable=True)
    alpha_score     = Column(Float, nullable=True)

    computed_at     = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<AlphaPatternStats {self.pattern_key} @ {self.computed_at}>"


class SetupQualityHistory(Base):
    """
    Histórico do Setup Quality Score calculado para cada sinal emitido.
    Permite rastrear a qualidade média dos setups ao longo do tempo.
    """
    __tablename__ = "setup_quality_history"

    id              = Column(Integer, primary_key=True, index=True)
    symbol          = Column(String(20), nullable=False, index=True)
    timeframe       = Column(String(10), nullable=False, default="1h")

    # Score de qualidade (0–100)
    quality_score       = Column(Float, nullable=False)
    signal              = Column(String(10), nullable=True)  # BUY | SELL | NEUTRAL
    regime              = Column(String(20), nullable=True)

    # Componentes do score (para auditoria)
    pattern_score       = Column(Float, nullable=True)   # 0–40: contribuição dos padrões
    regime_score        = Column(Float, nullable=True)   # 0–25: contribuição do regime
    context_score_comp  = Column(Float, nullable=True)   # 0–20: contribuição do contexto
    confluence_score    = Column(Float, nullable=True)   # 0–15: quantidade de critérios

    # Critérios ativos
    criteria_met        = Column(Text, nullable=True)    # JSON list
    criteria_count      = Column(Integer, nullable=True)

    # Resultado (preenchido ao resolver)
    outcome             = Column(String(10), nullable=True)  # WIN | LOSS | OPEN
    pnl_pct             = Column(Float, nullable=True)

    computed_at         = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<SetupQualityHistory {self.symbol} score={self.quality_score:.1f} @ {self.computed_at}>"
