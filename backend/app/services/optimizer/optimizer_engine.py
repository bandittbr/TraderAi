"""
Fase 8 — Optimizer Engine (Orquestrador)
Coordena: criterion_performance → combination_analyzer → regime_performance
          → weight_engine → persiste OptimizationSnapshot
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.database import AsyncSessionLocal
from app.models.optimizer import OptimizationSnapshot
from app.services.optimizer.criterion_performance import criterion_performance_engine, CriterionPerformanceReport
from app.services.optimizer.combination_analyzer import combination_analyzer, CombinationReport
from app.services.optimizer.regime_performance import regime_performance_analyzer, RegimeReport
from app.services.optimizer.weight_engine import weight_engine, WeightSnapshot

logger = logging.getLogger(__name__)


@dataclass
class OptimizationResult:
    criterion_report: CriterionPerformanceReport
    combination_report: CombinationReport
    regime_report: RegimeReport
    weight_snapshot: WeightSnapshot
    snapshot_id: Optional[int] = None
    computed_at: Optional[datetime] = None


class OptimizerEngine:
    """Orquestrador principal da Fase 8."""

    async def run(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = 90,
        save_snapshot: bool          = True,
    ) -> OptimizationResult:
        """
        Executa ciclo completo de otimização:
        1. Calcula performance por critério
        2. Analisa combinações
        3. Analisa por regime
        4. Atualiza pesos dinâmicos
        5. Persiste snapshot
        """
        logger.info("[optimizer] Iniciando ciclo de otimização (symbol=%s, days=%d)", symbol, lookback_days)

        # 1. Criterion performance
        criterion_report = await criterion_performance_engine.compute(symbol, lookback_days)
        logger.info("[optimizer] Critérios analisados: %d", len(criterion_report.criteria))

        # 2. Combinations
        combo_report = await combination_analyzer.compute(symbol, lookback_days)
        logger.info("[optimizer] Combinações válidas: %d", combo_report.valid)

        # 3. Regime
        regime_report = await regime_performance_analyzer.compute(symbol, lookback_days)
        logger.info("[optimizer] Regimes analisados: %d", len(regime_report.regimes))

        # 4. Update weights
        new_weights = await weight_engine.update_weights(criterion_report)
        weight_snap = WeightSnapshot(weights=new_weights, computed_at=datetime.utcnow())

        result = OptimizationResult(
            criterion_report   = criterion_report,
            combination_report = combo_report,
            regime_report      = regime_report,
            weight_snapshot    = weight_snap,
            computed_at        = datetime.utcnow(),
        )

        # 5. Persist snapshot
        if save_snapshot and criterion_report.total_resolved >= 5:
            snap_id = await self._save_snapshot(symbol, result)
            result.snapshot_id = snap_id

        return result

    async def _save_snapshot(self, symbol: Optional[str], result: OptimizationResult) -> Optional[int]:
        """Persiste OptimizationSnapshot no banco."""
        try:
            cr = result.criterion_report
            combo = result.combination_report
            regime = result.regime_report

            # Top combos JSON (max 10)
            top_combos = [
                {
                    "criteria": list(c.criteria),
                    "win_rate": c.win_rate,
                    "profit_factor": c.profit_factor,
                    "sample_size": c.sample_size,
                    "expectancy": c.expectancy,
                    "score": c.score,
                }
                for c in combo.top_all[:10]
            ]

            # Regime JSON
            regime_data = {}
            for name, rd in regime.regimes.items():
                regime_data[name] = {
                    "n": rd.total_signals,
                    "baseline_wr": rd.baseline_wr,
                    "baseline_pf": rd.baseline_pf,
                    "best": rd.best_criteria,
                    "avoid": rd.avoid_criteria,
                }

            snap = OptimizationSnapshot(
                symbol              = symbol,
                total_resolved      = cr.total_resolved,
                baseline_wr         = cr.baseline_wr,
                baseline_pf         = cr.baseline_pf,
                baseline_exp        = cr.baseline_exp,
                weights_json        = json.dumps(result.weight_snapshot.weights),
                top_criteria_json   = json.dumps(cr.top_criteria),
                worst_criteria_json = json.dumps(cr.worst_criteria),
                top_combos_json     = json.dumps(top_combos),
                regime_json         = json.dumps(regime_data),
                computed_at         = result.computed_at,
            )
            async with AsyncSessionLocal() as db:
                db.add(snap)
                await db.commit()
                await db.refresh(snap)
                return snap.id
        except Exception as e:
            logger.error("[optimizer] _save_snapshot: %s", e)
            return None

    async def get_latest_snapshot(self) -> Optional[OptimizationSnapshot]:
        """Retorna o snapshot mais recente do banco."""
        from sqlalchemy import select
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(OptimizationSnapshot)
                    .order_by(OptimizationSnapshot.computed_at.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error("[optimizer] get_latest_snapshot: %s", e)
            return None


optimizer_engine = OptimizerEngine()
