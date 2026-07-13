"""
Groq Agent — API Endpoints
Dashboard do Groq Agent: conta, trades, thinking, stats.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Query
from sqlalchemy import select, desc, func as sqlfunc

from app.database import AsyncSessionLocal
from app.models.groq_agent import GroqTrade, GroqAccount, GroqThinking
from app.services.groq_agent.trade_engine import groq_engine
from app.services.groq_agent.risk_manager import groq_risk

router = APIRouter(prefix="/groq", tags=["Groq Agent"])


# ── GET /groq/account ────────────────────────────────────────────────────────
@router.get("/account")
async def get_account():
    """Conta do Groq Agent."""
    acc = await groq_engine.get_account()
    return {
        "balance": acc.balance,
        "initial_balance": acc.initial_balance,
        "peak_balance": acc.peak_balance,
        "total_pnl": acc.total_pnl,
        "total_trades": acc.total_trades,
        "winning_trades": acc.winning_trades,
        "losing_trades": acc.losing_trades,
    }


# ── GET /groq/stats ──────────────────────────────────────────────────────────
@router.get("/stats")
async def get_stats(days: int = Query(30, ge=1, le=365)):
    """Estatísticas do Groq Agent."""
    return await groq_engine.get_stats(days)


# ── GET /groq/trades ─────────────────────────────────────────────────────────
@router.get("/trades")
async def get_trades(
    status: str = Query("ALL"),
    limit: int = Query(50, ge=1, le=200),
):
    """Trades do Groq Agent."""
    async with AsyncSessionLocal() as session:
        q = select(GroqTrade).order_by(desc(GroqTrade.opened_at))
        if status == "OPEN":
            q = q.where(GroqTrade.status == "OPEN")
        elif status == "CLOSED":
            q = q.where(GroqTrade.status == "CLOSED")
        q = q.limit(limit)
        result = await session.execute(q)
        trades = result.scalars().all()

    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.trade_side,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "quantity": t.quantity,
            "stop_loss": t.stop_loss_price,
            "take_profit": t.take_profit_price,
            "pnl": t.pnl,
            "pnl_pct": t.pnl_pct,
            "net_pnl_pct": t.net_pnl_pct,
            "status": t.status,
            "close_reason": t.close_reason,
            "confidence": t.confidence,
            "regime": t.regime_at_entry,
            "opened_at": str(t.opened_at),
            "closed_at": str(t.closed_at) if t.closed_at else None,
            "duration_minutes": t.duration_minutes,
        }
        for t in trades
    ]


# ── GET /groq/thinking ───────────────────────────────────────────────────────
@router.get("/thinking")
async def get_thinking(limit: int = Query(20, ge=1, le=100)):
    """Pensamentos recentes do Groq (raciocínio do LLM)."""
    thinking = await groq_engine.get_recent_thinking(limit)
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "action": t.action,
            "confidence": t.confidence,
            "reasoning": t.reasoning,
            "model": t.model_used,
            "latency_ms": t.latency_ms,
            "prompt_tokens": t.prompt_tokens,
            "output_tokens": t.output_tokens,
            "error": t.error,
            "created_at": str(t.created_at),
        }
        for t in thinking
    ]


# ── GET /groq/chart-data ─────────────────────────────────────────────────────
@router.get("/chart-data")
async def get_chart_data(symbol: str = "BTCUSDT", limit: int = 200):
    """Dados de trades para o gráfico (markers)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(GroqTrade).where(
                GroqTrade.symbol == symbol,
            ).order_by(desc(GroqTrade.opened_at)).limit(limit)
        )
        trades = result.scalars().all()

    return {
        "trades": [
            {
                "trade_id": t.id,
                "open_time": int(t.opened_at.timestamp()) if t.opened_at else 0,
                "open_price": t.entry_price,
                "side": t.trade_side,
                "confidence": t.confidence,
                "close_time": int(t.closed_at.timestamp()) if t.closed_at else None,
                "close_price": t.exit_price,
                "pnl": t.pnl,
                "pnl_pct": t.net_pnl_pct,
                "reason": t.close_reason,
                "is_open": t.status == "OPEN",
            }
            for t in trades
        ]
    }


# ── GET /groq/debug ──────────────────────────────────────────────────────────
@router.get("/debug")
async def get_debug():
    """Debug info do Groq Agent."""
    return {
        "signals_processed": groq_engine._signals_processed,
        "last_execution": str(groq_engine._last_execution) if groq_engine._last_execution else None,
        "consecutive_losses": groq_risk.consecutive_losses,
        "is_paused": groq_risk.is_paused,
        "sizing_factor": groq_risk.sizing_factor(),
        "model": "llama-3.3-70b-versatile",
        "frequency": "60s",
    }
