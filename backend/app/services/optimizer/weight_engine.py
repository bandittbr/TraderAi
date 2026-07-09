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


# ── Regimes suportados ────────────────────────────────────────────────────────
ALL_REGIMES = ("GLOBAL", "BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY")
DEFAULT_REGIME = "GLOBAL"


class DynamicWeightEngine:
    """
    Mantém e atualiza pesos adaptativos para cada critério canônico.
    V7: pesos separados por regime de mercado (GLOBAL, BULL, BEAR, SIDEWAYS, HIGH_VOL).
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

    async def load_weights(self, regime: str = DEFAULT_REGIME) -> dict[str, float]:
        """
        Carrega pesos de um regime específico.
        Se não existirem pesos para o regime, retorna os pesos GLOBAL como fallback,
        ou defaults se nem GLOBAL existir.
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(CriterionWeight).where(CriterionWeight.regime == regime)
                )
                rows = result.scalars().all()
                if rows:
                    return {r.criterion: float(r.weight) for r in rows}
        except Exception as e:
            logger.error("[weights] load(%s): %s", regime, e)

        # Fallback: tenta GLOBAL
        if regime != DEFAULT_REGIME:
            logger.info("[weights] Regime %s sem dados — fallback para GLOBAL", regime)
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(CriterionWeight).where(CriterionWeight.regime == DEFAULT_REGIME)
                    )
                    rows = result.scalars().all()
                    if rows:
                        return {r.criterion: float(r.weight) for r in rows}
            except Exception as e:
                logger.error("[weights] load(GLOBAL fallback): %s", e)

        return {c: DEFAULT_WEIGHT for c in ALL_CANONICAL}

    async def load_all_regime_weights(self) -> dict[str, dict[str, float]]:
        """
        V7: Carrega TODOS os pesos de todos os regimes.
        Retorna {regime: {criterion: weight}}.
        Útil para o scheduler manter cache completo.
        """
        result: dict[str, dict[str, float]] = {}
        try:
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(select(CriterionWeight))).scalars().all()
                for r in rows:
                    regime = r.regime or DEFAULT_REGIME
                    if regime not in result:
                        result[regime] = {}
                    result[regime][r.criterion] = float(r.weight)
        except Exception as e:
            logger.error("[weights] load_all: %s", e)

        # Garantir que todos os regimes conhecidos estão presentes
        for regime in ALL_REGIMES:
            if regime not in result or not result[regime]:
                result[regime] = {c: DEFAULT_WEIGHT for c in ALL_CANONICAL}

        return result

    async def save_weights(self, weights: dict[str, float],
                           regime: str = DEFAULT_REGIME) -> None:
        """Persiste pesos de um regime no banco (upsert por regime+criterion)."""
        try:
            async with AsyncSessionLocal() as db:
                for criterion, weight in weights.items():
                    result = await db.execute(
                        select(CriterionWeight).where(
                            CriterionWeight.regime == regime,
                            CriterionWeight.criterion == criterion,
                        )
                    )
                    existing = result.scalar_one_or_none()
                    if existing:
                        existing.weight     = weight
                        existing.updated_at = datetime.utcnow()
                    else:
                        db.add(CriterionWeight(
                            regime     = regime,
                            criterion  = criterion,
                            weight     = weight,
                            updated_at = datetime.utcnow(),
                        ))
                await db.commit()
        except Exception as e:
            logger.error("[weights] save(%s): %s", regime, e)

    async def update_weights(
        self,
        report: CriterionPerformanceReport,
        regime: str = DEFAULT_REGIME,
    ) -> dict[str, float]:
        """
        Ciclo completo para um regime: carrega pesos atuais → calcula novos → persiste.
        Retorna os novos pesos para o regime.
        """
        current  = await self.load_weights(regime)
        new_weights = self.compute_new_weights(report, current)
        await self.save_weights(new_weights, regime)
        logger.info("[weights] Regime %s — pesos atualizados: %s", regime, new_weights)
        return new_weights

    def compute_new_weights_from_stats(
        self,
        criteria_stats: list,
        baseline_wr: float,
        baseline_pf: float,
        current: dict[str, float],
        min_sample: int = MIN_SAMPLE_WEIGHT,
    ) -> dict[str, float]:
        """
        V7: Versão simplificada de compute_new_weights que aceita uma lista
        de objetos com atributos: criterion, win_rate, profit_factor, resolved.
        Usado pelo optimizer para atualizar pesos por regime de mercado.
        """
        new_weights: dict[str, float] = {}
        bl_wr = baseline_wr or 50.0
        bl_pf = baseline_pf or 1.0

        for stats in criteria_stats:
            criterion  = stats.criterion
            cur_weight = current.get(criterion, DEFAULT_WEIGHT)

            if stats.sample_size < min_sample:
                new_weights[criterion] = cur_weight
                continue

            wr_delta = (stats.win_rate - bl_wr) / max(bl_wr, 1.0)
            pf_delta = (stats.profit_factor - bl_pf) / max(bl_pf, 0.01)
            performance_delta = (wr_delta + pf_delta) / 2.0

            raw_adj = performance_delta * SCALE_FACTOR
            clamped = max(-MAX_DELTA, min(MAX_DELTA, raw_adj))
            new_w   = cur_weight + clamped
            new_weights[criterion] = round(max(MIN_WEIGHT, min(MAX_WEIGHT, new_w)), 2)

        for c in ALL_CANONICAL:
            if c not in new_weights:
                new_weights[c] = current.get(c, DEFAULT_WEIGHT)

        return new_weights

    async def get_current_snapshot(self, regime: str = DEFAULT_REGIME) -> WeightSnapshot:
        """Retorna snapshot atual dos pesos de um regime."""
        weights = await self.load_weights(regime)
        return WeightSnapshot(
            weights     = weights,
            computed_at = datetime.utcnow(),
        )


weight_engine = DynamicWeightEngine()
