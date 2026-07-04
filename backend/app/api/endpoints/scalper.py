"""
Scalper Engine — API Endpoints (Fase 13)
Todos independentes dos endpoints de Paper Trading.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Query
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models.scalper import (
    ScalperAccount, ScalperTrade, ScalperRiskDaily, ScalperSignal
)
from app.schemas.scalper import (
    ScalperAccountOut, ScalperTradeOut, ScalperRiskOut,
    ScalperSignalOut, ScalperStatsOut, ScalperDebugOut,
)
from app.services.scalper.stats import get_scalper_stats
from app.services.scalper.trade_engine import scalper_engine
from app.services.scalper.risk_manager import scalper_risk

router = APIRouter()


# ── GET /scalper/account ──────────────────────────────────────────────────────
@router.get("/account", response_model=ScalperAccountOut)
async def get_scalper_account():
    """Saldo e patrimônio da conta do Scalper."""
    async with AsyncSessionLocal() as session:
        acc = await session.scalar(select(ScalperAccount))
        if acc is None:
            from app.services.scalper.trade_engine import INITIAL_BALANCE
            acc = ScalperAccount(
                balance=INITIAL_BALANCE, initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            session.add(acc)
            await session.commit()
            await session.refresh(acc)
        return ScalperAccountOut.model_validate(acc)


# ── GET /scalper/trades ───────────────────────────────────────────────────────
@router.get("/trades", response_model=list[ScalperTradeOut])
async def get_scalper_trades(
    status: str | None = Query(None, description="OPEN ou CLOSED"),
    limit:  int        = Query(50, ge=1, le=500),
):
    """Lista trades do Scalper."""
    async with AsyncSessionLocal() as session:
        q = select(ScalperTrade).order_by(desc(ScalperTrade.opened_at)).limit(limit)
        if status:
            q = q.where(ScalperTrade.status == status.upper())
        result = await session.execute(q)
        trades = list(result.scalars().all())
    return [ScalperTradeOut.model_validate(t) for t in trades]


# ── GET /scalper/stats ────────────────────────────────────────────────────────
@router.get("/stats", response_model=ScalperStatsOut)
async def get_scalper_stats_endpoint(
    days: int = Query(30, ge=1, le=365),
):
    """Estatísticas de performance do Scalper."""
    data = await get_scalper_stats(days=days)
    return ScalperStatsOut(**data)


# ── GET /scalper/risk ─────────────────────────────────────────────────────────
@router.get("/risk", response_model=ScalperRiskOut)
async def get_scalper_risk():
    """Estado de risco do dia atual."""
    today = date.today().isoformat()
    async with AsyncSessionLocal() as session:
        row = await session.scalar(
            select(ScalperRiskDaily).where(ScalperRiskDaily.date == today)
        )
        if row is None:
            row = ScalperRiskDaily(date=today)
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return ScalperRiskOut.model_validate(row)


# ── GET /scalper/risk/history ─────────────────────────────────────────────────
@router.get("/risk/history", response_model=list[ScalperRiskOut])
async def get_scalper_risk_history(
    days: int = Query(7, ge=1, le=90),
):
    """Histórico de risco dos últimos N dias."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ScalperRiskDaily)
            .where(ScalperRiskDaily.date >= cutoff)
            .order_by(desc(ScalperRiskDaily.date))
        )
        rows = list(result.scalars().all())
    return [ScalperRiskOut.model_validate(r) for r in rows]


# ── GET /scalper/signals ──────────────────────────────────────────────────────
@router.get("/signals", response_model=list[ScalperSignalOut])
async def get_scalper_signals(
    symbol: str | None = Query(None),
    limit:  int        = Query(100, ge=1, le=500),
):
    """Histórico de sinais gerados pelo Scalper."""
    async with AsyncSessionLocal() as session:
        q = select(ScalperSignal).order_by(desc(ScalperSignal.emitted_at)).limit(limit)
        if symbol:
            q = q.where(ScalperSignal.symbol == symbol.upper())
        result = await session.execute(q)
        sigs = list(result.scalars().all())
    return [ScalperSignalOut.model_validate(s) for s in sigs]


# ── GET /scalper/debug ────────────────────────────────────────────────────────
@router.get("/debug", response_model=ScalperDebugOut)
async def get_scalper_debug():
    """Informações de diagnóstico do Scalper Engine."""
    info = await scalper_engine.get_debug_info()
    return ScalperDebugOut(**info)
