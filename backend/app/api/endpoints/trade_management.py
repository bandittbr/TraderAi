"""
TradeAI — Endpoints de Trade Management (Fase 12)

Rota base: /api/v1/trade-management/
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter
from sqlalchemy import select, func as sqlfunc

from app.database import AsyncSessionLocal
from app.models.paper_trading import PaperTrade, TradeStatus, TradeSide
from app.models.trade_management import TradeLifecycle
from app.schemas.trade_management import (
    TradeManagementStats,
    TradeManagementStatus,
    ActiveTradeDetail,
    TradeLifecycleEvent,
)
from app.config import settings

router = APIRouter()


# ── Active Trades with Phase 12 details ──────────────────────────────────────

@router.get(
    "/active",
    response_model=List[ActiveTradeDetail],
    summary="Trades abertos com detalhes Phase 12",
)
async def get_active_trades() -> List[ActiveTradeDetail]:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PaperTrade).where(PaperTrade.status == TradeStatus.OPEN.value)
        )
        trades = list(result.scalars().all())

    out: List[ActiveTradeDetail] = []
    for t in trades:
        opened_utc = (
            t.opened_at if t.opened_at and t.opened_at.tzinfo
            else (t.opened_at.replace(tzinfo=timezone.utc) if t.opened_at else now)
        )
        hours = round((now - opened_utc).total_seconds() / 3600, 2)
        max_h = settings.paper_max_hours_open
        remaining_h = max(0.0, round(max_h - hours, 2))

        out.append(ActiveTradeDetail(
            id                   = t.id,
            symbol               = t.symbol,
            side                 = t.trade_side or "LONG",
            entry_price          = t.entry_price or 0.0,
            quantity             = t.quantity or 0.0,
            opened_at            = opened_utc,
            hours_open           = hours,
            max_hours            = max_h,
            time_stop_in_hours   = remaining_h,
            break_even_activated = bool(t.break_even_activated),
            trailing_stop_active = bool(t.trailing_stop_active),
            trailing_stop_price  = t.trailing_stop_price,
            tp1_hit              = bool(t.tp1_hit),
            remaining_quantity   = t.remaining_quantity,
            estimated_exit_score = t.exit_score_at_close,  # None for open trades
            pnl_unrealized       = None,
            pnl_unrealized_pct   = None,
        ))
    return out


# ── Lifecycle of a specific trade ─────────────────────────────────────────────

@router.get(
    "/lifecycle/{trade_id}",
    response_model=TradeManagementStatus,
    summary="Ciclo de vida completo de um trade",
)
async def get_trade_lifecycle(trade_id: int) -> TradeManagementStatus:
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        t_result = await session.execute(
            select(PaperTrade).where(PaperTrade.id == trade_id)
        )
        trade = t_result.scalar_one_or_none()

        lc_result = await session.execute(
            select(TradeLifecycle)
            .where(TradeLifecycle.trade_id == trade_id)
            .order_by(TradeLifecycle.created_at.asc())
        )
        events = list(lc_result.scalars().all())

    if trade is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Trade {trade_id} não encontrado")

    opened_utc = (
        trade.opened_at if trade.opened_at and trade.opened_at.tzinfo
        else (trade.opened_at.replace(tzinfo=timezone.utc) if trade.opened_at else now)
    )
    hours = round((now - opened_utc).total_seconds() / 3600, 2)

    lifecycle = [
        TradeLifecycleEvent(
            id         = e.id,
            trade_id   = e.trade_id,
            event_type = e.event_type,
            price      = e.price,
            quantity   = e.quantity,
            pnl        = e.pnl,
            notes      = e.notes,
            created_at = e.created_at,
        )
        for e in events
    ]

    return TradeManagementStatus(
        trade_id              = trade.id,
        symbol                = trade.symbol,
        side                  = trade.trade_side or "LONG",
        entry_price           = trade.entry_price or 0.0,
        current_price         = trade.exit_price,
        hours_open            = hours,
        break_even_activated  = bool(trade.break_even_activated),
        break_even_timestamp  = trade.break_even_timestamp,
        trailing_stop_active  = bool(trade.trailing_stop_active),
        trailing_stop_price   = trade.trailing_stop_price,
        trailing_stop_peak    = trade.trailing_stop_peak,
        tp1_hit               = bool(trade.tp1_hit),
        tp1_partial_price     = trade.tp1_partial_price,
        tp1_partial_qty       = trade.tp1_partial_qty,
        tp1_partial_pnl       = trade.partial_pnl,
        remaining_quantity    = trade.remaining_quantity,
        exit_score            = trade.exit_score_at_close,
        lifecycle             = lifecycle,
    )


# ── Statistics ────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=TradeManagementStats,
    summary="Estatísticas do Trade Management Engine",
)
async def get_trade_management_stats() -> TradeManagementStats:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PaperTrade).where(PaperTrade.status == TradeStatus.CLOSED.value)
        )
        trades = list(result.scalars().all())

    if not trades:
        return TradeManagementStats(
            total_closed_trades=0, avg_duration_hours=0.0,
            time_stop_count=0, break_even_stop_count=0, trailing_stop_count=0,
            stop_loss_count=0, take_profit_count=0, signal_close_count=0,
            exit_score_count=0, partial_tp_count=0,
            time_stop_rate_pct=0.0, trailing_stop_rate_pct=0.0,
            partial_tp_rate_pct=0.0, avg_exit_score=None,
            avg_pnl_time_stop=None, avg_pnl_trailing_stop=None,
            avg_pnl_take_profit=None, avg_pnl_stop_loss=None,
        )

    n = len(trades)

    def _dur_h(t: PaperTrade) -> float:
        if not t.opened_at or not t.closed_at:
            return 0.0
        op = t.opened_at if t.opened_at.tzinfo else t.opened_at.replace(tzinfo=timezone.utc)
        cl = t.closed_at if t.closed_at.tzinfo else t.closed_at.replace(tzinfo=timezone.utc)
        return (cl - op).total_seconds() / 3600

    def _avg_pnl(subset: list) -> Optional[float]:
        if not subset:
            return None
        return round(sum(t.pnl or 0 for t in subset) / len(subset), 6)

    reason_map = {
        "TIME_STOP":       "time_stop",
        "BREAK_EVEN_STOP": "break_even_stop",
        "TRAILING_STOP":   "trailing_stop",
        "STOP_LOSS":       "stop_loss",
        "TAKE_PROFIT":     "take_profit",
        "SIGNAL_CLOSE":    "signal_close",
        "EXIT_SCORE":      "exit_score",
    }

    counts: dict = {k: [] for k in reason_map.values()}
    for t in trades:
        key = reason_map.get(t.close_reason or "", None)
        if key:
            counts[key].append(t)

    partial_count = sum(1 for t in trades if t.tp1_hit)
    durations     = [_dur_h(t) for t in trades]
    avg_dur       = round(sum(durations) / n, 2)

    exit_scores = [t.exit_score_at_close for t in trades if t.exit_score_at_close is not None]

    return TradeManagementStats(
        total_closed_trades    = n,
        avg_duration_hours     = avg_dur,
        time_stop_count        = len(counts["time_stop"]),
        break_even_stop_count  = len(counts["break_even_stop"]),
        trailing_stop_count    = len(counts["trailing_stop"]),
        stop_loss_count        = len(counts["stop_loss"]),
        take_profit_count      = len(counts["take_profit"]),
        signal_close_count     = len(counts["signal_close"]),
        exit_score_count       = len(counts["exit_score"]),
        partial_tp_count       = partial_count,
        time_stop_rate_pct     = round(len(counts["time_stop"])     / n * 100, 2),
        trailing_stop_rate_pct = round(len(counts["trailing_stop"]) / n * 100, 2),
        partial_tp_rate_pct    = round(partial_count / n * 100, 2),
        avg_exit_score         = round(sum(exit_scores) / len(exit_scores), 2) if exit_scores else None,
        avg_pnl_time_stop      = _avg_pnl(counts["time_stop"]),
        avg_pnl_trailing_stop  = _avg_pnl(counts["trailing_stop"]),
        avg_pnl_take_profit    = _avg_pnl(counts["take_profit"]),
        avg_pnl_stop_loss      = _avg_pnl(counts["stop_loss"]),
    )


# ── Lifecycle history (last N events) ────────────────────────────────────────

@router.get(
    "/events",
    response_model=List[TradeLifecycleEvent],
    summary="Últimos N eventos de ciclo de vida",
)
async def get_recent_lifecycle_events(limit: int = 50) -> List[TradeLifecycleEvent]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(TradeLifecycle)
            .order_by(TradeLifecycle.created_at.desc())
            .limit(limit)
        )
        events = list(result.scalars().all())

    return [
        TradeLifecycleEvent(
            id         = e.id,
            trade_id   = e.trade_id,
            event_type = e.event_type,
            price      = e.price,
            quantity   = e.quantity,
            pnl        = e.pnl,
            notes      = e.notes,
            created_at = e.created_at,
        )
        for e in events
    ]
