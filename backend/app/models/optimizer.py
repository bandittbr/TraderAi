"""
Fase 8 — Optimizer ORM Models
Tabelas: criterion_weights, optimization_snapshots
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, Float, Integer, String, Text, func
from app.database import Base


class CriterionWeight(Base):
    """
    Peso adaptativo para cada critério canônico.
    Atualizado pelo DynamicWeightEngine a cada ciclo de otimização.
    """
    __tablename__ = "criterion_weights"

    id         = Column(Integer, primary_key=True, index=True)
    criterion  = Column(String(40), nullable=False, unique=True, index=True)
    weight     = Column(Float, nullable=False, default=10.0)  # 1.0 – 20.0
    updated_at = Column(DateTime, nullable=False, default=func.now())

    def __repr__(self) -> str:
        return f"<CriterionWeight {self.criterion}={self.weight:.2f}>"


class OptimizationSnapshot(Base):
    """
    Snapshot de uma rodada de otimização.
    Armazena métricas baseline, pesos utilizados e top combinações.
    """
    __tablename__ = "optimization_snapshots"

    id             = Column(Integer, primary_key=True, index=True)
    symbol         = Column(String(20), nullable=True)     # None = global
    total_resolved = Column(Integer, default=0)
    baseline_wr    = Column(Float, nullable=True)
    baseline_pf    = Column(Float, nullable=True)
    baseline_exp   = Column(Float, nullable=True)

    # JSON snapshots
    weights_json        = Column(Text, nullable=True)   # {criterion: weight}
    top_criteria_json   = Column(Text, nullable=True)   # [criterion, ...]
    worst_criteria_json = Column(Text, nullable=True)
    top_combos_json     = Column(Text, nullable=True)   # [{criteria, wr, pf, n}, ...]
    regime_json         = Column(Text, nullable=True)   # {regime: {best, avoid}}

    # Comparativo V5 vs V6
    v5_win_rate       = Column(Float, nullable=True)
    v5_profit_factor  = Column(Float, nullable=True)
    v5_sharpe         = Column(Float, nullable=True)
    v5_drawdown       = Column(Float, nullable=True)
    v5_expectancy     = Column(Float, nullable=True)
    v6_win_rate       = Column(Float, nullable=True)
    v6_profit_factor  = Column(Float, nullable=True)
    v6_sharpe         = Column(Float, nullable=True)
    v6_drawdown       = Column(Float, nullable=True)
    v6_expectancy     = Column(Float, nullable=True)

    computed_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    def __repr__(self) -> str:
        return f"<OptimizationSnapshot {self.symbol or 'global'} @ {self.computed_at}>"
