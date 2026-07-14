"""
Fase 11 — Strategy Evolution Engine — ORM
Tabelas: strategy_library, strategy_versions, strategy_backtests, strategy_robustness
"""
from __future__ import annotations
import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, Float, String, Boolean, Text, DateTime, ForeignKey, Index
)
from app.database import Base
from app.logger import get_logger

logger = get_logger(__name__)


class StrategyLibrary(Base):
    """
    Catálogo mestre de estratégias descobertas.
    status: CANDIDATE | TESTING | APPROVED | REJECTED | ACTIVE
    """
    __tablename__ = "strategy_library"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    strategy_key    = Column(String(128), unique=True, nullable=False)   # hash determinístico
    name            = Column(String(256), nullable=False)
    generation      = Column(Integer, default=0)                         # geração evolutiva
    parent_ids      = Column(Text, default="[]")                         # JSON list de IDs pai
    origin          = Column(String(32), default="GENERATED")            # GENERATED | MUTATED | CROSSOVER

    # Regras (JSON auditável)
    entry_rules     = Column(Text, nullable=False)
    exit_rules      = Column(Text, nullable=False)
    risk_rules      = Column(Text, nullable=False)

    # Status
    status          = Column(String(32), default="CANDIDATE")
    rejection_reason = Column(Text, nullable=True)

    # Métricas consolidadas (melhor backtest aprovado)
    win_rate        = Column(Float, default=0.0)
    profit_factor   = Column(Float, default=0.0)
    sharpe          = Column(Float, default=0.0)
    calmar          = Column(Float, default=0.0)
    expectancy      = Column(Float, default=0.0)
    max_drawdown    = Column(Float, default=0.0)
    n_trades        = Column(Integer, default=0)

    # Score composto 0-100
    strategy_score  = Column(Float, default=0.0)
    rank_position   = Column(Integer, nullable=True)                     # posição no ranking global

    # Robustez
    wf_score        = Column(Float, nullable=True)
    mc_ruin_prob    = Column(Float, nullable=True)
    stability_score = Column(Float, nullable=True)
    robustness_score = Column(Float, nullable=True)
    is_robust       = Column(Boolean, default=False)

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_evaluated  = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_strategy_status",   "status"),
        Index("ix_strategy_score",    "strategy_score"),
        Index("ix_strategy_rank",     "rank_position"),
        Index("ix_strategy_gen",      "generation"),
    )

    def entry_rules_dict(self) -> dict:
        try: return json.loads(self.entry_rules)
        except Exception as e:
            logger.warning(f"StrategyLibrary.entry_rules_dict: {e}", exc_info=True)
            return {}

    def exit_rules_dict(self) -> dict:
        try: return json.loads(self.exit_rules)
        except Exception as e:
            logger.warning(f"StrategyLibrary.exit_rules_dict: {e}", exc_info=True)
            return {}

    def risk_rules_dict(self) -> dict:
        try: return json.loads(self.risk_rules)
        except Exception as e:
            logger.warning(f"StrategyLibrary.risk_rules_dict: {e}", exc_info=True)
            return {}


class StrategyVersion(Base):
    """Histórico de versões e evoluções de uma estratégia."""
    __tablename__ = "strategy_versions"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id     = Column(Integer, ForeignKey("strategy_library.id"), nullable=False)
    version         = Column(Integer, default=1)
    change_type     = Column(String(32))         # MUTATION | CROSSOVER | INITIAL
    change_summary  = Column(Text, nullable=True)
    entry_rules     = Column(Text, nullable=False)
    exit_rules      = Column(Text, nullable=False)
    risk_rules      = Column(Text, nullable=False)
    strategy_score  = Column(Float, default=0.0)
    created_at      = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_sv_strategy_id", "strategy_id"),
    )


class StrategyBacktest(Base):
    """Resultado de um backtest de uma estratégia específica."""
    __tablename__ = "strategy_backtests"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id     = Column(Integer, ForeignKey("strategy_library.id"), nullable=False)
    symbol          = Column(String(32), nullable=True)    # None = todos os símbolos
    period_days     = Column(Integer, default=90)
    n_trades        = Column(Integer, default=0)
    win_rate        = Column(Float, default=0.0)
    profit_factor   = Column(Float, default=0.0)
    sharpe          = Column(Float, default=0.0)
    calmar          = Column(Float, default=0.0)
    expectancy      = Column(Float, default=0.0)
    max_drawdown    = Column(Float, default=0.0)
    avg_win_pct     = Column(Float, default=0.0)
    avg_loss_pct    = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    strategy_score  = Column(Float, default=0.0)
    executed_at     = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_sb_strategy_id", "strategy_id"),
        Index("ix_sb_score",       "strategy_score"),
    )


class StrategyRobustness(Base):
    """Resultado da validação de robustez de uma estratégia."""
    __tablename__ = "strategy_robustness"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id     = Column(Integer, ForeignKey("strategy_library.id"), nullable=False, unique=True)
    wf_score        = Column(Float, default=0.0)
    wf_is_robust    = Column(Boolean, default=False)
    mc_ruin_prob    = Column(Float, default=0.0)
    mc_dd_p95       = Column(Float, default=0.0)
    stability_score = Column(Float, default=0.0)
    n_unstable_cells = Column(Integer, default=0)
    robustness_score = Column(Float, default=0.0)
    approved        = Column(Boolean, default=False)
    rejection_reason = Column(Text, nullable=True)
    evaluated_at    = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_sr_strategy_id",  "strategy_id"),
        Index("ix_sr_approved",     "approved"),
    )
