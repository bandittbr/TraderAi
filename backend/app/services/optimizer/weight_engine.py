"""
Fase 8 — Dynamic Weight Engine
Ajusta pesos dos critérios de forma lenta e estável com base na performance histórica.
Regras:
  - Peso inicial: 10.0
  - Limites: [1.0, 20.0]
  - Ajuste máximo por ciclo: ±1.0
  - Apenas pesos de critérios — nunca SL/TP/risco
  - Tudo determinístico e auditável
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.optimizer import CriterionWeight
from app.services.optimizer.criterion_performance import (
    ALL_CANONICAL, CriterionStats, CriterionPerformanceReport
)

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_WEIGHT  = 10.0
MIN_WEIGHT      = 1.0
MAX_WEIGHT      = 20.0
MAX_DELTA       = 1.0    # ajuste máximo por ciclo
SCALE_FACTOR    = 5.0    # amplificação da diferença de performance
MIN_SAMPLE_WEIGHT = 5    # mínimo de trades para ajustar peso


@dataclass
class WeightSnapshot:
    """Snapshot atual de todos os pesos."""
    weights:    dict[str, float] = field(default_factory=dict)   # {criterion: weight}
    computed_at: Optional[datetime] = None
    total_signals: int = 0


class DynamicWeightEngine:
    """
    Mantém e atualiza pesos adaptativos para cada critério canônico.
    Os pesos são persistidos em `criterion_weights` no banco de dados.
    """

    def compute_new_weights(
        self,
        report:   CriterionPerformanceReport,
        current:  dict[str, float],
    ) -> dict[str, float]:
        """
        Computa novos pesos com base na performance relativa ao baseline.
        Ajuste lento: max ±1.0 por ciclo.
        """
        new_weights: dict[str, float] = {}
        baseline_wr = report.baseline_wr or 50.0
        baseline_pf = report.baseline_pf or 1.0

        for stats in report.criteria:
            criterion     = stats.criterion
            cur_weight    = current.get(criterion, DEFAULT_WEIGHT)

            if not stats.sufficient_data or stats.resolved < MIN_SAMPLE_WEIGHT:
                # Sem dados suficientes: manter peso atual (nenhuma mudança)
                new_weights[criterion] = cur_weight
                continue

            # Delta relativo ao baseline
            wr_delta = (stats.win_rate - baseline_wr) / max(baseline_wr, 1.0)
            pf_delta = (stats.profit_factor - baseline_pf) / max(baseline_pf, 0.01)

            # Penalizar critérios com drawdown alto
            dd_penalty = max(0.0, stats.max_drawdown / 10.0)

            # Score combinado
            performance_delta = (wr_delta + pf_delta) / 2.0 - dd_penalty

            # Ajuste com limite de velocidade
            raw_adj   = performance_delta * SCALE_FACTOR
            clamped   = max(-MAX_DELTA, min(MAX_DELTA, raw_adj))
            new_w     = cur_weight + clamped

            # Clamp absoluto
            new_weights[criterion] = round(max(MIN_WEIGHT, min(MAX_WEIGHT, new_w)), 2)

        # Garantir que todos os critérios têm peso
        for c in ALL_CANONICAL:
            if c not in new_weights:
                new_weights[c] = current.get(c, DEFAULT_WEIGHT)

        return new_weights

    async def load_weights(self) -> dict[str, float]:
        """Carrega pesos do banco. Retorna defaults se não existir."""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(CriterionWeight))
                rows = result.scalars().all()
                if rows:
                    return {r.criterion: float(r.weight) for r in rows}
        except Exception as e:
            logger.error("[weights] load: %s", e)
        return {c: DEFAULT_WEIGHT for c in ALL_CANONICAL}

    async def save_weights(self, weights: dict[str, float]) -> None:
        """Persiste pesos no banco (upsert por criterion)."""
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        try:
            async with AsyncSessionLocal() as db:
                for criterion, weight in weights.items():
                    # Delete + re-insert (simples e compatível com SQLite)
                    result = await db.execute(
                        select(CriterionWeight).where(CriterionWeight.criterion == criterion)
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.weight     = weight
                        existing.updated_at = datetime.utcnow()
                    else:
                        db.add(CriterionWeight(
                            criterion  = criterion,
                            weight     = weight,
                            updated_at = datetime.utcnow(),
                        ))
                await db.commit()
        except Exception as e:
            logger.error("[weights] save: %s", e)

    async def update_weights(
        self,
        report: CriterionPerformanceReport,
    ) -> dict[str, float]:
        """
        Ciclo completo: carrega pesos atuais → calcula novos → persiste.
        Retorna os novos pesos.
        """
        current  = await self.load_weights()
        new_weights = self.compute_new_weights(report, current)
        await self.save_weights(new_weights)
        logger.info("[weights] Pesos atualizados: %s", new_weights)
        return new_weights

    async def get_current_snapshot(self) -> WeightSnapshot:
        """Retorna snapshot atual dos pesos."""
        weights = await self.load_weights()
        return WeightSnapshot(
            weights     = weights,
            computed_at = datetime.utcnow(),
        )


weight_engine = DynamicWeightEngine()
