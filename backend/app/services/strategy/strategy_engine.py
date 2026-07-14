"""
Fase 11 — Strategy Engine (Orquestrador)
Generator → Evaluator → Robustness → Evolution → Ranking Top 100
Determinístico, auditável, sem IA.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

BATCH_EVALUATE    = 200    # estratégias avaliadas por ciclo
TOP_N_RANKING     = 100
MIN_SCORE_APPROVE = 50.0   # score mínimo para robustness check
MIN_TRADES_APPROVE = 5


@dataclass
class EngineRunResult:
    """Resultado de um ciclo completo do Strategy Engine."""
    n_generated:   int = 0
    n_evaluated:   int = 0
    n_approved:    int = 0
    n_evolved:     int = 0
    top_score:     float = 0.0
    top_strategy:  Optional[str] = None
    computed_at:   datetime = field(default_factory=datetime.utcnow)


class StrategyEngine:
    """
    Orquestra o ciclo completo de descoberta e evolução de estratégias.
    """

    async def run(
        self,
        generate_new:  bool = True,
        evolve:        bool = True,
        validate_rob:  bool = True,
        batch:         int  = BATCH_EVALUATE,
    ) -> EngineRunResult:
        """Ciclo completo: gerar → avaliar → robustez → evoluir → ranking."""
        result = EngineRunResult()

        # 1. Gerar novas estratégias (se solicitado)
        if generate_new:
            n_new = await self._generate_and_persist(batch)
            result.n_generated = n_new

        # 2. Avaliar candidatos pendentes
        n_eval = await self._evaluate_pending(batch)
        result.n_evaluated = n_eval

        # 3. Validar robustez das melhores estratégias (se solicitado)
        if validate_rob:
            n_app = await self._validate_robustness()
            result.n_approved = n_app

        # 4. Evoluir estratégias aprovadas (se solicitado)
        if evolve:
            n_evo = await self._evolve()
            result.n_evolved = n_evo

        # 5. Atualizar ranking Top 100
        await self._update_ranking()

        # 6. Buscar top estratégia
        top = await self._get_top_strategy()
        if top:
            result.top_score    = top[1]
            result.top_strategy = top[0]

        logger.info(
            "[strategy_engine] ciclo concluído: gen=%d eval=%d approved=%d evo=%d",
            result.n_generated, result.n_evaluated, result.n_approved, result.n_evolved,
        )
        return result

    # ── Internos ──────────────────────────────────────────────────────────────

    async def _generate_and_persist(self, batch: int) -> int:
        """Gera estratégias e persiste no banco (apenas as ainda não existentes)."""
        from app.services.strategy.generator import strategy_generator
        from app.models.strategies import StrategyLibrary

        all_strategies = strategy_generator.generate_all(limit=batch)
        n_new = 0
        try:
            async with AsyncSessionLocal() as db:
                for sdef in all_strategies:
                    exists = await db.execute(
                        select(StrategyLibrary.id).where(StrategyLibrary.strategy_key == sdef.strategy_key)
                    )
                    if exists.scalar_one_or_none() is not None:
                        continue
                    obj = StrategyLibrary(
                        strategy_key = sdef.strategy_key,
                        name         = sdef.name,
                        generation   = sdef.generation,
                        parent_ids   = json.dumps(sdef.parent_ids),
                        origin       = sdef.origin,
                        entry_rules  = json.dumps(sdef.entry_rules),
                        exit_rules   = json.dumps(sdef.exit_rules),
                        risk_rules   = json.dumps(sdef.risk_rules),
                        status       = "CANDIDATE",
                    )
                    db.add(obj)
                    n_new += 1
                await db.commit()
        except Exception as exc:
            logger.error("[strategy_engine] _generate_and_persist: %s", exc)
        return n_new

    async def _evaluate_pending(self, batch: int) -> int:
        """Avalia as estratégias em status CANDIDATE (as mais antigas primeiro)."""
        from app.services.strategy.evaluator import strategy_evaluator
        from app.models.strategies import StrategyLibrary, StrategyBacktest

        n_eval = 0
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(StrategyLibrary)
                    .where(StrategyLibrary.status == "CANDIDATE")
                    .order_by(StrategyLibrary.created_at)
                    .limit(batch)
                )
                result = await db.execute(q)
                candidates = list(result.scalars().all())

            for strat in candidates:
                try:
                    entry  = json.loads(strat.entry_rules)
                    exit_r = json.loads(strat.exit_rules)
                    risk   = json.loads(strat.risk_rules)

                    bt = await strategy_evaluator.evaluate(
                        entry_rules=entry, exit_rules=exit_r, risk_rules=risk,
                        strategy_key=strat.strategy_key,
                    )

                    async with AsyncSessionLocal() as db:
                        strat_obj = await db.get(StrategyLibrary, strat.id)
                        if strat_obj is None:
                            continue
                        strat_obj.win_rate        = bt.win_rate
                        strat_obj.profit_factor   = bt.profit_factor
                        strat_obj.sharpe          = bt.sharpe
                        strat_obj.calmar          = bt.calmar
                        strat_obj.expectancy      = bt.expectancy
                        strat_obj.max_drawdown    = bt.max_drawdown
                        strat_obj.n_trades        = bt.n_trades
                        strat_obj.strategy_score  = bt.strategy_score
                        strat_obj.last_evaluated  = bt.executed_at
                        # Avançar status
                        if bt.n_trades < MIN_TRADES_APPROVE:
                            strat_obj.status = "REJECTED"
                            strat_obj.rejection_reason = "TRADES_INSUFICIENTES"
                        elif bt.strategy_score >= MIN_SCORE_APPROVE:
                            strat_obj.status = "TESTING"
                        else:
                            strat_obj.status = "REJECTED"
                            strat_obj.rejection_reason = f"SCORE_BAIXO={bt.strategy_score:.1f}"
                        await db.commit()

                    # Persistir backtest detalhado
                    await strategy_evaluator.persist(bt, strat.id)
                    n_eval += 1
                except Exception as exc:
                    logger.warning("[strategy_engine] evaluate strat %d: %s", strat.id, exc)
        except Exception as exc:
            logger.error("[strategy_engine] _evaluate_pending: %s", exc)
        return n_eval

    async def _validate_robustness(self) -> int:
        """Executa validação de robustez para estratégias em TESTING."""
        from app.models.strategies import StrategyLibrary, StrategyRobustness
        from app.services.robustness.walk_forward import walk_forward_validator
        from app.services.robustness.monte_carlo  import monte_carlo_engine
        from app.services.robustness.stability    import strategy_stability_analyzer

        n_approved = 0
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(StrategyLibrary)
                    .where(StrategyLibrary.status == "TESTING")
                    .order_by(StrategyLibrary.strategy_score.desc())
                    .limit(20)    # até 20 por ciclo
                )
                result  = await db.execute(q)
                testing = list(result.scalars().all())

            for strat in testing:
                try:
                    wf  = await walk_forward_validator.validate(pattern_key=strat.strategy_key, persist=False)
                    mc  = await monte_carlo_engine.simulate(pattern_key=strat.strategy_key, persist=False)
                    st  = await strategy_stability_analyzer.analyze(pattern_key=strat.strategy_key, persist=False)

                    # Score de robustez composto
                    rob_score = _compute_robustness_score(wf, mc, st)
                    approved  = rob_score >= 40.0 and mc.ruin_probability < 30.0

                    async with AsyncSessionLocal() as db:
                        strat_obj = await db.get(StrategyLibrary, strat.id)
                        if strat_obj is None:
                            continue
                        strat_obj.wf_score        = wf.wf_score
                        strat_obj.mc_ruin_prob     = mc.ruin_probability
                        strat_obj.stability_score  = st.overall_stability_score
                        strat_obj.robustness_score = rob_score
                        strat_obj.is_robust        = approved
                        strat_obj.status           = "APPROVED" if approved else "REJECTED"
                        if not approved:
                            strat_obj.rejection_reason = f"ROBUSTEZ_INSUF={rob_score:.1f}"
                        await db.commit()

                    # Persistir robustness separado
                    async with AsyncSessionLocal() as db:
                        rob_obj = StrategyRobustness(
                            strategy_id    = strat.id,
                            wf_score       = wf.wf_score,
                            wf_is_robust   = wf.is_robust,
                            mc_ruin_prob   = mc.ruin_probability,
                            mc_dd_p95      = mc.dd_p95,
                            stability_score = st.overall_stability_score,
                            n_unstable_cells = st.n_unstable_cells,
                            robustness_score = rob_score,
                            approved       = approved,
                            rejection_reason = None if approved else f"rob={rob_score:.1f}",
                        )
                        db.add(rob_obj)
                        await db.commit()

                    if approved:
                        n_approved += 1
                except Exception as exc:
                    logger.warning("[strategy_engine] robustness strat %d: %s", strat.id, exc)
        except Exception as exc:
            logger.error("[strategy_engine] _validate_robustness: %s", exc)
        return n_approved

    async def _evolve(self) -> int:
        """Gera novas estratégias por evolução das aprovadas."""
        from app.models.strategies import StrategyLibrary
        from app.services.strategy.generator import StrategyDef
        from app.services.strategy.evaluator import BacktestResult
        from app.services.strategy.evolution_engine import evolution_engine

        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(StrategyLibrary)
                    .where(StrategyLibrary.status == "APPROVED")
                    .order_by(StrategyLibrary.strategy_score.desc())
                    .limit(50)
                )
                result   = await db.execute(q)
                approved = list(result.scalars().all())

            if not approved:
                return 0

            # Reconstruir (StrategyDef, BacktestResult) pairs
            pairs = []
            for s in approved:
                sdef = StrategyDef(
                    strategy_key = s.strategy_key,
                    name         = s.name,
                    entry_rules  = json.loads(s.entry_rules),
                    exit_rules   = json.loads(s.exit_rules),
                    risk_rules   = json.loads(s.risk_rules),
                    generation   = s.generation,
                    origin       = s.origin,
                )
                bt = BacktestResult(
                    strategy_key=s.strategy_key, symbol=None, period_days=90,
                    n_trades=s.n_trades, win_rate=s.win_rate,
                    profit_factor=s.profit_factor, sharpe=s.sharpe,
                    calmar=s.calmar, expectancy=s.expectancy,
                    max_drawdown=s.max_drawdown, avg_win_pct=0.0, avg_loss_pct=0.0,
                    total_return_pct=0.0, strategy_score=s.strategy_score,
                    executed_at=s.last_evaluated or datetime.utcnow(),
                )
                pairs.append((sdef, bt))

            new_strategies = await evolution_engine.evolve(pairs, max_new=50)

            # Persistir novos candidatos
            n_new = 0
            async with AsyncSessionLocal() as db:
                for sdef in new_strategies:
                    exists = await db.execute(
                        select(StrategyLibrary.id).where(StrategyLibrary.strategy_key == sdef.strategy_key)
                    )
                    if exists.scalar_one_or_none() is not None:
                        continue
                    obj = StrategyLibrary(
                        strategy_key = sdef.strategy_key,
                        name         = sdef.name,
                        generation   = sdef.generation,
                        parent_ids   = json.dumps(sdef.parent_ids),
                        origin       = sdef.origin,
                        entry_rules  = json.dumps(sdef.entry_rules),
                        exit_rules   = json.dumps(sdef.exit_rules),
                        risk_rules   = json.dumps(sdef.risk_rules),
                        status       = "CANDIDATE",
                    )
                    db.add(obj)
                    n_new += 1
                await db.commit()
            return n_new
        except Exception as exc:
            logger.error("[strategy_engine] _evolve: %s", exc)
            return 0

    async def _update_ranking(self) -> None:
        """Atualiza posições no ranking Top 100 das estratégias aprovadas."""
        from app.models.strategies import StrategyLibrary
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(StrategyLibrary)
                    .where(StrategyLibrary.status == "APPROVED")
                    .order_by(StrategyLibrary.strategy_score.desc())
                    .limit(TOP_N_RANKING)
                )
                result  = await db.execute(q)
                top100  = list(result.scalars().all())

                for pos, strat in enumerate(top100, start=1):
                    strat_obj = await db.get(StrategyLibrary, strat.id)
                    if strat_obj:
                        strat_obj.rank_position = pos
                await db.commit()
        except Exception as exc:
            logger.error("[strategy_engine] _update_ranking: %s", exc)

    async def _get_top_strategy(self) -> Optional[tuple[str, float]]:
        """Retorna (name, score) da estratégia #1 do ranking."""
        from app.models.strategies import StrategyLibrary
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(StrategyLibrary)
                    .where(StrategyLibrary.rank_position == 1)
                    .limit(1)
                )
                result = await db.execute(q)
                top    = result.scalar_one_or_none()
                if top:
                    return (top.name, top.strategy_score)
        except Exception as e:
            logger.warning(f"strategy_engine[_get_top_strategy]: {e}", exc_info=True)
        return None


def _compute_robustness_score(wf, mc, st) -> float:
    """Score de robustez composto para avaliação de estratégias."""
    components = []
    if wf and wf.n_trades_total > 0:
        components.append((wf.wf_score, 0.40))
    if mc and mc.n_trades > 0:
        ruin_pen = min(mc.ruin_probability * 2.0, 50.0)
        dd_pen   = max(0.0, (mc.dd_p95 - 10.0) * 1.5)
        mc_score = max(0.0, 100.0 - ruin_pen - dd_pen)
        components.append((mc_score, 0.35))
    if st and st.n_total_trades > 0:
        components.append((st.overall_stability_score, 0.25))
    if not components:
        return 0.0
    total_w = sum(w for _, w in components)
    return round(sum(s * (w / total_w) for s, w in components), 1)


# ── Singleton ─────────────────────────────────────────────────────────────────

strategy_engine = StrategyEngine()
