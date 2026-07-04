"""
Fase 9 — Alpha Engine Orchestrator
Orquestra o ciclo completo de análise alpha:
  1. AlphaPatternEngine — padrões positivos e negativos
  2. MetaAnalyticsEngine — melhores dimensões
  3. SetupQualityScorer — score de qualidade de setup
Persiste resultados e expõe snapshot para a API.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.services.alpha.pattern_engine import AlphaPatternEngine, AlphaReport, alpha_pattern_engine
from app.services.alpha.meta_analytics import MetaAnalyticsEngine, MetaAnalyticsReport, meta_analytics_engine
from app.services.alpha.quality_scorer import SetupQualityScorer, setup_quality_scorer

logger = logging.getLogger(__name__)


@dataclass
class AlphaEngineResult:
    """Resultado completo de um ciclo de análise alpha."""
    computed_at:    datetime         = field(default_factory=datetime.utcnow)
    pattern_report: Optional[AlphaReport]        = None
    meta_report:    Optional[MetaAnalyticsReport] = None
    success:        bool             = False
    error:          Optional[str]    = None


class AlphaEngine:
    """Orquestra análise alpha completa."""

    _last_result: Optional[AlphaEngineResult] = None

    async def run(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = 90,
    ) -> AlphaEngineResult:
        """Executa ciclo completo de análise alpha."""
        logger.info("[alpha] Iniciando ciclo de análise alpha. symbol=%s", symbol)
        result = AlphaEngineResult()

        try:
            # 1. Análise de padrões
            result.pattern_report = await alpha_pattern_engine.compute(
                symbol=symbol, lookback_days=lookback_days, persist=True
            )
            logger.info(
                "[alpha] Padrões: %d best, %d worst",
                len(result.pattern_report.best_patterns),
                len(result.pattern_report.worst_patterns),
            )

            # 2. Meta-analytics
            result.meta_report = await meta_analytics_engine.compute(
                lookback_days=lookback_days
            )
            logger.info(
                "[alpha] Meta: best_symbol=%s, best_regime=%s",
                result.meta_report.best_symbol,
                result.meta_report.best_regime,
            )

            result.success    = True
            result.computed_at = datetime.utcnow()
            self.__class__._last_result = result

        except Exception as exc:
            logger.error("[alpha] run error: %s", exc)
            result.error   = str(exc)
            result.success = False

        return result

    @classmethod
    def get_latest(cls) -> Optional[AlphaEngineResult]:
        """Retorna o último resultado calculado (em memória)."""
        return cls._last_result

    @property
    def pattern_engine(self) -> AlphaPatternEngine:
        return alpha_pattern_engine

    @property
    def meta_engine(self) -> MetaAnalyticsEngine:
        return meta_analytics_engine

    @property
    def quality_scorer(self) -> SetupQualityScorer:
        return setup_quality_scorer


# ── Singleton ─────────────────────────────────────────────────────────────────

alpha_engine = AlphaEngine()
