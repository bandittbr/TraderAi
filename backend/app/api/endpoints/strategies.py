"""
Fase 11 — Endpoints da Strategy API
5 rotas: /strategies, /strategies/top, /strategies/{id},
         /strategies/evolve, /strategies/backtest
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from app.schemas.strategies import (
    StrategyResponse,
    StrategyListResponse,
    BacktestResponse,
    EvolveResponse,
    RobustnessDetailResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _to_response(strat) -> StrategyResponse:
    """Converte ORM → schema."""
    try: entry = json.loads(strat.entry_rules)
    except: entry = {}
    try: exit_r = json.loads(strat.exit_rules)
    except: exit_r = {}
    try: risk = json.loads(strat.risk_rules)
    except: risk = {}
    try: parents = json.loads(strat.parent_ids)
    except: parents = []

    return StrategyResponse(
        id               = strat.id,
        strategy_key     = strat.strategy_key,
        name             = strat.name,
        generation       = strat.generation,
        origin           = strat.origin,
        status           = strat.status,
        win_rate         = strat.win_rate or 0.0,
        profit_factor    = strat.profit_factor or 0.0,
        sharpe           = strat.sharpe or 0.0,
        calmar           = strat.calmar or 0.0,
        expectancy       = strat.expectancy or 0.0,
        max_drawdown     = strat.max_drawdown or 0.0,
        n_trades         = strat.n_trades or 0,
        strategy_score   = strat.strategy_score or 0.0,
        rank_position    = strat.rank_position,
        wf_score         = strat.wf_score,
        mc_ruin_prob     = strat.mc_ruin_prob,
        stability_score  = strat.stability_score,
        robustness_score = strat.robustness_score,
        is_robust        = bool(strat.is_robust),
        rejection_reason = strat.rejection_reason,
        entry_rules      = entry,
        exit_rules       = exit_r,
        risk_rules       = risk,
        parent_ids       = parents,
        created_at       = strat.created_at,
        last_evaluated   = strat.last_evaluated,
    )


@router.get("", response_model=StrategyListResponse)
async def list_strategies(
    status: Optional[str] = Query(None, description="CANDIDATE|TESTING|APPROVED|REJECTED"),
    limit:  int           = Query(50, ge=1, le=200),
    offset: int           = Query(0, ge=0),
):
    """Lista estratégias com filtro de status e paginação."""
    from app.models.strategies import StrategyLibrary
    from app.database import AsyncSessionLocal
    from sqlalchemy import select, func

    try:
        async with AsyncSessionLocal() as db:
            q = select(StrategyLibrary).order_by(StrategyLibrary.strategy_score.desc())
            if status:
                q = q.where(StrategyLibrary.status == status.upper())
            count_q = select(func.count()).select_from(q.subquery())
            total   = (await db.execute(count_q)).scalar_one()
            result  = await db.execute(q.offset(offset).limit(limit))
            rows    = list(result.scalars().all())
        return StrategyListResponse(
            total      = total,
            strategies = [_to_response(r) for r in rows],
        )
    except Exception as exc:
        logger.error("[strategies] list: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/top", response_model=list[StrategyResponse])
async def get_top_strategies(
    limit: int = Query(20, ge=1, le=100),
):
    """Retorna o Top N estratégias aprovadas por ranking."""
    from app.models.strategies import StrategyLibrary
    from app.database import AsyncSessionLocal
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            q = (
                select(StrategyLibrary)
                .where(
                    StrategyLibrary.status == "APPROVED",
                    StrategyLibrary.rank_position.isnot(None),
                )
                .order_by(StrategyLibrary.rank_position)
                .limit(limit)
            )
            result = await db.execute(q)
            rows   = list(result.scalars().all())
        return [_to_response(r) for r in rows]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Retorna detalhes completos de uma estratégia específica."""
    from app.models.strategies import StrategyLibrary
    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            strat = await db.get(StrategyLibrary, strategy_id)
        if not strat:
            raise HTTPException(status_code=404, detail="Estratégia não encontrada")
        return _to_response(strat)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/evolve", response_model=EvolveResponse)
async def run_evolution(
    batch:        int  = Query(200, ge=10, le=2000),
    generate_new: bool = Query(True),
    validate_rob: bool = Query(False),   # desligado por default (pesado)
    evolve:       bool = Query(True),
):
    """
    Executa um ciclo de evolução: gerar → avaliar → evoluir.
    Estratégias novas ficam em CANDIDATE — nunca substituem a ativa.
    """
    from app.services.strategy.strategy_engine import strategy_engine

    try:
        report = await strategy_engine.run(
            generate_new = generate_new,
            evolve       = evolve,
            validate_rob = validate_rob,
            batch        = batch,
        )
        return EvolveResponse(
            status        = "ok",
            n_generated   = report.n_generated,
            n_evaluated   = report.n_evaluated,
            n_approved    = report.n_approved,
            n_evolved     = report.n_evolved,
            top_score     = report.top_score,
            top_strategy  = report.top_strategy,
            computed_at   = report.computed_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/backtest/{strategy_id}", response_model=BacktestResponse)
async def backtest_strategy(
    strategy_id: int,
    symbol:      Optional[str] = Query(None),
    period_days: int           = Query(90, ge=7, le=365),
):
    """
    Executa um backtest avulso de uma estratégia específica.
    Resultado é salvo no histórico mas não altera status da estratégia.
    """
    from app.models.strategies import StrategyLibrary
    from app.services.strategy.evaluator import strategy_evaluator
    from app.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            strat = await db.get(StrategyLibrary, strategy_id)
        if not strat:
            raise HTTPException(status_code=404, detail="Estratégia não encontrada")

        entry  = json.loads(strat.entry_rules)
        exit_r = json.loads(strat.exit_rules)
        risk   = json.loads(strat.risk_rules)

        bt = await strategy_evaluator.evaluate(
            entry_rules=entry, exit_rules=exit_r, risk_rules=risk,
            strategy_key=strat.strategy_key, symbol=symbol, period_days=period_days,
        )
        await strategy_evaluator.persist(bt, strategy_id)

        return BacktestResponse(
            strategy_id      = strategy_id,
            strategy_key     = strat.strategy_key,
            symbol           = bt.symbol,
            period_days      = bt.period_days,
            n_trades         = bt.n_trades,
            win_rate         = bt.win_rate,
            profit_factor    = bt.profit_factor,
            sharpe           = bt.sharpe,
            calmar           = bt.calmar,
            expectancy       = bt.expectancy,
            max_drawdown     = bt.max_drawdown,
            total_return_pct = bt.total_return_pct,
            strategy_score   = bt.strategy_score,
            executed_at      = bt.executed_at,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
