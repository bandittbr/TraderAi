"""
TradeAI - Endpoints: Trade Activity
API para consultar o log de atividades dos agentes e estatísticas.
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.trade_activity import get_activities, get_agent_stats

router = APIRouter()


class ActivityOut(BaseModel):
    id: int
    agent: str
    event: str
    symbol: str
    trade_id: Optional[int] = None
    price: float
    quantity: Optional[float] = None
    side: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    reason: Optional[str] = None
    confidence: Optional[float] = None
    regime: Optional[str] = None
    balance_after: Optional[float] = None
    timestamp: Optional[int] = None

    class Config:
        from_attributes = True


class AgentStatsOut(BaseModel):
    agent: str
    period_days: int
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    current_balance: Optional[float] = None
    best_trade_pnl: Optional[float] = None
    worst_trade_pnl: Optional[float] = None


@router.get("/activities", response_model=list[ActivityOut])
async def list_activities(
    agent: Optional[str] = Query(None, description="Filtrar por agente: paper, scalper, worker"),
    symbol: Optional[str] = Query(None, description="Filtrar por símbolo: BTCUSDT"),
    event: Optional[str] = Query(None, description="Filtrar por evento: open, close"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Lista atividades de trade com filtros opcionais."""
    activities = await get_activities(
        agent=agent, symbol=symbol, event=event,
        limit=limit, offset=offset,
    )
    return [
        ActivityOut(
            id=a.id, agent=a.agent, event=a.event, symbol=a.symbol,
            trade_id=a.trade_id, price=a.price, quantity=a.quantity,
            side=a.side, pnl=a.pnl, pnl_pct=a.pnl_pct, reason=a.reason,
            confidence=a.confidence, regime=a.regime, balance_after=a.balance_after,
            timestamp=int(a.created_at.timestamp() * 1000) if a.created_at else None,
        )
        for a in activities
    ]


@router.get("/stats/{agent}", response_model=AgentStatsOut)
async def agent_stats(
    agent: str,
    days: int = Query(30, ge=1, le=365),
):
    """Retorna estatísticas de um agente baseadas no log de atividades."""
    stats = await get_agent_stats(agent, days=days)
    return AgentStatsOut(**stats)


@router.get("/chart-data/{agent}")
async def chart_data(
    agent: str,
    symbol: str = Query("BTCUSDT"),
    limit: int = Query(200, ge=1, le=1000),
):
    """
    Retorna dados de trades para plotar no gráfico.
    Cada trade é um marker: open (entry) + close (exit) com P&L.
    """
    activities = await get_activities(agent=agent, symbol=symbol, limit=limit)

    # Agrupar por trade_id para montar pares open/close
    trades = {}
    for a in activities:
        tid = a.trade_id or a.id
        if tid not in trades:
            trades[tid] = {}
        if a.event == "open":
            trades[tid]["open"] = {
                "time": int(a.created_at.timestamp()) if a.created_at else 0,
                "price": a.price,
                "side": a.side,
                "confidence": a.confidence,
            }
        elif a.event == "close":
            trades[tid]["close"] = {
                "time": int(a.created_at.timestamp()) if a.created_at else 0,
                "price": a.price,
                "pnl": a.pnl,
                "pnl_pct": a.pnl_pct,
                "reason": a.reason,
            }

    # Converter para lista ordenada por tempo de abertura
    result = []
    for tid, data in sorted(trades.items(), key=lambda x: x[1].get("open", {}).get("time", 0)):
        if "open" in data:
            entry = data["open"]
            exit_data = data.get("close")
            result.append({
                "trade_id": tid,
                "open_time": entry["time"],
                "open_price": entry["price"],
                "side": entry["side"],
                "confidence": entry["confidence"],
                "close_time": exit_data["time"] if exit_data else None,
                "close_price": exit_data["price"] if exit_data else None,
                "pnl": exit_data["pnl"] if exit_data else None,
                "pnl_pct": exit_data["pnl_pct"] if exit_data else None,
                "reason": exit_data["reason"] if exit_data else None,
                "is_open": exit_data is None,
            })

    return {"agent": agent, "symbol": symbol, "trades": result}
