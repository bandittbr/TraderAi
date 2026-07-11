"""
TradeAI - Trade Activity Service
Registra cada ação dos agentes e transmite via WebSocket.

Fluxo:
  1. Agente abre/fecha trade → chama log_activity()
  2. log_activity() salva no DB + broadcast via WebSocket
  3. Frontend recebe em tempo real → renderiza markers no gráfico
"""

import json
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.trade_activity import TradeActivity
from app.services.websocket.manager import ws_manager
from app.logger import get_logger

logger = get_logger(__name__)


async def log_activity(
    agent: str,
    event: str,
    symbol: str,
    price: float,
    *,
    trade_id: int | None = None,
    quantity: float | None = None,
    side: str | None = None,
    pnl: float | None = None,
    pnl_pct: float | None = None,
    reason: str | None = None,
    confidence: float | None = None,
    regime: str | None = None,
    balance_after: float | None = None,
    extra: dict | None = None,
) -> TradeActivity:
    """
    Registra um evento de trade e transmite via WebSocket.
    
    Args:
        agent: Nome do agente ("paper", "scalper", "worker")
        event: Tipo do evento ("open", "close", "update", "signal")
        symbol: Par de trading ("BTCUSDT")
        price: Preço no momento do evento
        trade_id: ID do trade na tabela original (opcional)
        quantity: Quantidade negociada (opcional)
        side: "LONG" ou "SHORT" (opcional)
        pnl: P&L em USD (opcional, só no close)
        pnl_pct: P&L em % (opcional, só no close)
        reason: Motivo do fechamento (opcional)
        confidence: Confiança do sinal 0-100 (opcional)
        regime: Regime de mercado (opcional)
        balance_after: Saldo da conta após o evento (opcional)
        extra: Dict com dados extras serializado como JSON (opcional)
    
    Returns:
        TradeActivity criado
    """
    activity = TradeActivity(
        agent=agent,
        event=event,
        symbol=symbol,
        trade_id=trade_id,
        price=price,
        quantity=quantity,
        side=side,
        pnl=pnl,
        pnl_pct=pnl_pct,
        reason=reason,
        confidence=confidence,
        regime=regime,
        balance_after=balance_after,
        extra=json.dumps(extra) if extra else None,
    )

    async with AsyncSessionLocal() as session:
        session.add(activity)
        await session.commit()
        await session.refresh(activity)

    # Broadcast via WebSocket
    try:
        payload = activity.to_dict()
        await ws_manager.broadcast(payload)
        logger.debug(f"[trade_activity] Broadcast: {agent} {event} {symbol} @ {price}")
    except Exception as e:
        logger.warning(f"[trade_activity] Broadcast falhou: {e}")

    return activity


async def get_activities(
    agent: str | None = None,
    symbol: str | None = None,
    event: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[TradeActivity]:
    """
    Busca atividades de trade com filtros opcionais.
    """
    async with AsyncSessionLocal() as session:
        query = select(TradeActivity).order_by(desc(TradeActivity.created_at))

        if agent:
            query = query.where(TradeActivity.agent == agent)
        if symbol:
            query = query.where(TradeActivity.symbol == symbol)
        if event:
            query = query.where(TradeActivity.event == event)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())


async def get_agent_stats(agent: str, days: int = 30) -> dict:
    """
    Retorna estatísticas de um agente baseadas no log de atividades.
    """
    from sqlalchemy import func as sqlfunc
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        # Total de trades
        total_q = await session.execute(
            select(sqlfunc.count(TradeActivity.id)).where(
                TradeActivity.agent == agent,
                TradeActivity.event == "close",
                TradeActivity.created_at >= since,
            )
        )
        total_trades = total_q.scalar() or 0

        # Wins
        wins_q = await session.execute(
            select(sqlfunc.count(TradeActivity.id)).where(
                TradeActivity.agent == agent,
                TradeActivity.event == "close",
                TradeActivity.pnl > 0,
                TradeActivity.created_at >= since,
            )
        )
        wins = wins_q.scalar() or 0

        # P&L total
        pnl_q = await session.execute(
            select(sqlfunc.sum(TradeActivity.pnl)).where(
                TradeActivity.agent == agent,
                TradeActivity.event == "close",
                TradeActivity.created_at >= since,
            )
        )
        total_pnl = pnl_q.scalar() or 0

        # Melhor trade
        best_q = await session.execute(
            select(TradeActivity).where(
                TradeActivity.agent == agent,
                TradeActivity.event == "close",
                TradeActivity.created_at >= since,
            ).order_by(desc(TradeActivity.pnl)).limit(1)
        )
        best_trade = best_q.scalar_one_or_none()

        # Pior trade
        worst_q = await session.execute(
            select(TradeActivity).where(
                TradeActivity.agent == agent,
                TradeActivity.event == "close",
                TradeActivity.created_at >= since,
            ).order_by(TradeActivity.pnl).limit(1)
        )
        worst_trade = worst_q.scalar_one_or_none()

        # Saldo atual
        last_q = await session.execute(
            select(TradeActivity).where(
                TradeActivity.agent == agent,
                TradeActivity.balance_after.isnot(None),
            ).order_by(desc(TradeActivity.created_at)).limit(1)
        )
        last_activity = last_q.scalar_one_or_none()
        current_balance = last_activity.balance_after if last_activity else None

        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        return {
            "agent": agent,
            "period_days": days,
            "total_trades": total_trades,
            "wins": wins,
            "losses": total_trades - wins,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "current_balance": current_balance,
            "best_trade_pnl": round(best_trade.pnl, 2) if best_trade else None,
            "worst_trade_pnl": round(worst_trade.pnl, 2) if worst_trade else None,
        }
