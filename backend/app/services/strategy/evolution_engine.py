"""
Fase 11 — Evolution Engine
Mutação + Crossover + Seleção por performance.
Tudo determinístico com seed fixa.
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from app.services.strategy.generator  import StrategyDef, strategy_generator
from app.services.strategy.evaluator  import strategy_evaluator, BacktestResult

logger = logging.getLogger(__name__)

EVOLUTION_SEED      = 42
TOP_PARENTS         = 20      # melhores estratégias usadas como pais
MAX_MUTATIONS_PER   = 3       # mutações por pai
MAX_CROSSOVERS      = 30      # crossovers por ciclo
MIN_SCORE_PARENT    = 40.0    # score mínimo para ser pai
MIN_TRADES_PARENT   = 5       # trades mínimos para ser pai


class EvolutionEngine:
    """
    Algoritmo evolutivo determinístico.
    Não usa random puro — usa random.Random com seed fixa para reprodutibilidade.
    """

    def __init__(self) -> None:
        self._rng = random.Random(EVOLUTION_SEED)

    async def evolve(
        self,
        candidates: list[tuple[StrategyDef, BacktestResult]],
        max_new:    int = 100,
    ) -> list[StrategyDef]:
        """
        Dado um conjunto de estratégias avaliadas, gera novas via mutação + crossover.
        candidates: lista de (StrategyDef, BacktestResult) ordenada por score desc.
        """
        # Selecionar pais
        parents = [
            sdef for sdef, res in candidates
            if res.strategy_score >= MIN_SCORE_PARENT and res.n_trades >= MIN_TRADES_PARENT
        ][:TOP_PARENTS]

        if not parents:
            logger.info("[evolution] nenhum pai qualificado — retornando vazio")
            return []

        new_strategies: list[StrategyDef] = []
        seen_keys: set[str] = set(s.strategy_key for s, _ in candidates)

        # ── Mutações ──────────────────────────────────────────────────────────
        for parent in parents:
            mutations = strategy_generator.mutate(parent, seed=EVOLUTION_SEED)
            for m in mutations[:MAX_MUTATIONS_PER]:
                if m.strategy_key not in seen_keys:
                    seen_keys.add(m.strategy_key)
                    new_strategies.append(m)
                    if len(new_strategies) >= max_new:
                        return new_strategies

        # ── Crossover ─────────────────────────────────────────────────────────
        n_cross = 0
        # Crossover determinístico: combinar pares em ordem
        for i, a in enumerate(parents):
            for b in parents[i + 1:]:
                child = strategy_generator.crossover(a, b)
                if child.strategy_key not in seen_keys:
                    seen_keys.add(child.strategy_key)
                    new_strategies.append(child)
                    n_cross += 1
                    if n_cross >= MAX_CROSSOVERS or len(new_strategies) >= max_new:
                        break
            if len(new_strategies) >= max_new:
                break

        logger.info(
            "[evolution] gerados %d novos candidatos (%d pais usados)",
            len(new_strategies), len(parents),
        )
        return new_strategies

    def select_top(
        self,
        candidates: list[tuple[StrategyDef, BacktestResult]],
        top_n:      int = 100,
    ) -> list[tuple[StrategyDef, BacktestResult]]:
        """Seleciona top N estratégias por score composto."""
        return sorted(
            [(s, r) for s, r in candidates if r.n_trades >= MIN_TRADES_PARENT],
            key=lambda x: x[1].strategy_score,
            reverse=True,
        )[:top_n]


# ── Singleton ─────────────────────────────────────────────────────────────────

evolution_engine = EvolutionEngine()
