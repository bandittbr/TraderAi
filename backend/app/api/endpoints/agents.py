"""
Multi-Agent Trading System — API Endpoints
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Query
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models.agent_trade import AgentAccount, AgentTrade
from app.schemas.agents import (
    AgentInfo, AgentAccountOut, AgentTradeOut, AgentStatsOut,
    AgentsListOut, AgentsLeaderboardOut, AgentsLeaderboardEntry,
)
from app.services.agents import agent_registry, multi_agent_engine, register_all_agents
from app.services.market_data.store import store

router = APIRouter()


# ── GET /agents ───────────────────────────────────────────────────────────────
@router.get("", response_model=AgentsListOut)
async def list_agents():
    """Lista todos os agentes registrados."""
    if agent_registry.count == 0:
        register_all_agents()
    agents = agent_registry.list_agents()
    return AgentsListOut(agents=[AgentInfo(**a) for a in agents])


# ── GET /agents/{name} ───────────────────────────────────────────────────────
@router.get("/{name}", response_model=AgentInfo)
async def get_agent(name: str):
    """Informações de um agente específico."""
    if agent_registry.count == 0:
        register_all_agents()
    agent = agent_registry.get(name)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agente '{name}' não encontrado")
    return AgentInfo(**agent.get_config())


# ── POST /agents/{name}/enable ───────────────────────────────────────────────
@router.post("/{name}/enable")
async def enable_agent(name: str):
    """Ativa um agente."""
    if agent_registry.count == 0:
        register_all_agents()
    ok = agent_registry.enable(name)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agente '{name}' não encontrado")
    return {"status": "ok", "agent": name, "enabled": True}


# ── POST /agents/{name}/disable ──────────────────────────────────────────────
@router.post("/{name}/disable")
async def disable_agent(name: str):
    """Desativa um agente."""
    if agent_registry.count == 0:
        register_all_agents()
    ok = agent_registry.disable(name)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agente '{name}' não encontrado")
    return {"status": "ok", "agent": name, "enabled": False}


# ── GET /agents/{name}/account ──────────────────────────────────────────────
@router.get("/{name}/account", response_model=AgentAccountOut)
async def get_agent_account(name: str):
    """Saldo e patrimônio de um agente."""
    async with AsyncSessionLocal() as session:
        acc = await session.scalar(
            select(AgentAccount).where(AgentAccount.agent_name == name)
        )
        if acc is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Conta do agente '{name}' não encontrada")
        return AgentAccountOut.model_validate(acc)


# ── GET /agents/{name}/trades ───────────────────────────────────────────────
@router.get("/{name}/trades", response_model=list[AgentTradeOut])
async def get_agent_trades(
    name: str,
    status: str | None = Query(None, description="OPEN ou CLOSED"),
    limit: int = Query(50, ge=1, le=500),
):
    """Lista trades de um agente."""
    async with AsyncSessionLocal() as session:
        q = select(AgentTrade).where(AgentTrade.agent_name == name).order_by(desc(AgentTrade.opened_at)).limit(limit)
        if status:
            q = q.where(AgentTrade.status == status.upper())
        result = await session.execute(q)
        trades = list(result.scalars().all())
    return [AgentTradeOut.model_validate(t) for t in trades]


# ── GET /agents/{name}/open-trades ──────────────────────────────────────────
@router.get("/{name}/open-trades", response_model=list[AgentTradeOut])
async def get_agent_open_trades(name: str):
    """Trades abertos de um agente com P&L não realizado."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentTrade).where(
                AgentTrade.status == "OPEN",
                AgentTrade.agent_name == name,
            )
        )
        open_trades = list(result.scalars().all())

    # Buscar preços atuais
    symbols = list(set(t.symbol for t in open_trades))
    current_prices = {}
    for sym in symbols:
        stat = await store.get_stats(sym)
        if stat:
            current_prices[sym] = stat.price

    for trade in open_trades:
        cp = current_prices.get(trade.symbol)
        if cp and cp > 0:
            if trade.trade_side == "LONG":
                pnl_pct = (cp - trade.entry_price) / trade.entry_price
            else:
                pnl_pct = (trade.entry_price - cp) / trade.entry_price
            pnl_pct_lev = pnl_pct * trade.leverage
            fee = 0.0016 * trade.leverage
            net_pnl_pct = pnl_pct_lev - fee
            pnl_usd = trade.quantity * abs(cp - trade.entry_price) * trade.leverage
            if trade.trade_side == "SHORT":
                pnl_usd = -pnl_usd if cp > trade.entry_price else pnl_usd
            else:
                pnl_usd = pnl_usd if cp > trade.entry_price else -pnl_usd
            trade.unrealized_pnl = round(pnl_usd, 2)
            trade.unrealized_pnl_pct = round(net_pnl_pct * 100, 2)

    return [AgentTradeOut.model_validate(t) for t in open_trades]


# ── GET /agents/{name}/stats ────────────────────────────────────────────────
@router.get("/{name}/stats", response_model=AgentStatsOut)
async def get_agent_stats(name: str, days: int = Query(30, ge=1, le=365)):
    """Estatísticas de um agente."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AgentTrade).where(
                AgentTrade.agent_name == name,
                AgentTrade.status == "CLOSED",
                AgentTrade.closed_at >= cutoff,
            )
        )
        trades = list(result.scalars().all())

        open_result = await session.execute(
            select(AgentTrade).where(
                AgentTrade.agent_name == name,
                AgentTrade.status == "OPEN",
            )
        )
        open_trades = list(open_result.scalars().all())

        acc = await session.scalar(
            select(AgentAccount).where(AgentAccount.agent_name == name)
        )

    if not trades:
        return AgentStatsOut(
            agent_name=name, period_days=days, total_trades=0,
            open_trades=len(open_trades),
            win_rate=0, profit_factor=0, total_pnl_usd=0, total_pnl_pct=0,
            avg_trade_pnl=0, avg_win_pct=0, avg_loss_pct=0,
            max_win_pct=0, max_loss_pct=0,
            net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            avg_duration_min=0,
            balance=acc.balance if acc else 100_000,
            initial_balance=acc.initial_balance if acc else 100_000,
            peak_balance=acc.peak_balance if acc else 100_000,
        )

    def _pnl(t):
        return t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0

    wins = [t for t in trades if _pnl(t) > 0]
    losses = [t for t in trades if _pnl(t) <= 0]
    wr = len(wins) / len(trades) * 100 if trades else 0
    gross_profit = sum(_pnl(t) for t in wins) if wins else 0
    gross_loss = abs(sum(_pnl(t) for t in losses)) if losses else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)
    total_pnl_pct = sum(_pnl(t) for t in trades)
    total_pnl_usd = sum(t.pnl or 0 for t in trades)
    avg_win = sum(_pnl(t) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(abs(_pnl(t)) for t in losses) / len(losses) if losses else 0
    max_win = max((_pnl(t) for t in wins), default=0)
    max_loss = min((_pnl(t) for t in losses), default=0)
    durations = [t.duration_minutes for t in trades if t.duration_minutes is not None]

    by_sym = {}
    for t in trades:
        s = t.symbol
        by_sym.setdefault(s, {"trades": 0, "pnl": 0.0, "wins": 0})
        by_sym[s]["trades"] += 1
        by_sym[s]["pnl"] += _pnl(t)
        if _pnl(t) > 0:
            by_sym[s]["wins"] += 1

    by_reason = {}
    for t in trades:
        r = t.close_reason or "UNKNOWN"
        by_reason[r] = by_reason.get(r, 0) + 1

    return AgentStatsOut(
        agent_name=name, period_days=days,
        total_trades=len(trades), open_trades=len(open_trades),
        win_rate=round(wr, 1), profit_factor=round(pf, 3),
        total_pnl_usd=round(total_pnl_usd, 4),
        total_pnl_pct=round(total_pnl_pct, 4),
        avg_trade_pnl=round(total_pnl_usd / len(trades), 4) if trades else 0,
        avg_win_pct=round(avg_win, 3), avg_loss_pct=round(avg_loss, 3),
        max_win_pct=round(max_win, 3), max_loss_pct=round(max_loss, 3),
        net_win_rate=round(wr, 1), net_profit_factor=round(pf, 3),
        total_net_pnl_pct=round(total_pnl_pct, 4),
        avg_duration_min=round(sum(durations) / len(durations), 1) if durations else 0,
        balance=round(acc.balance, 2) if acc else 100_000,
        initial_balance=round(acc.initial_balance, 2) if acc else 100_000,
        peak_balance=round(acc.peak_balance, 2) if acc else 100_000,
        by_symbol=by_sym, by_reason=by_reason,
    )


# ── GET /agents/leaderboard ──────────────────────────────────────────────────
@router.get("/leaderboard", response_model=AgentsLeaderboardOut)
async def get_agents_leaderboard(days: int = Query(30, ge=1, le=365)):
    """Leaderboard de todos os agentes."""
    if agent_registry.count == 0:
        register_all_agents()

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = []

    async with AsyncSessionLocal() as session:
        for agent_info in agent_registry.list_agents():
            name = agent_info["name"]
            try:
                result = await session.execute(
                    select(AgentTrade).where(
                        AgentTrade.agent_name == name,
                        AgentTrade.status == "CLOSED",
                        AgentTrade.closed_at >= cutoff,
                    )
                )
                trades = list(result.scalars().all())

                acc = await session.scalar(
                    select(AgentAccount).where(AgentAccount.agent_name == name)
                )

                def _pnl(t):
                    return t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0

                wins = [t for t in trades if _pnl(t) > 0]
                wr = len(wins) / len(trades) * 100 if trades else 0
                gp = sum(_pnl(t) for t in wins)
                gl = abs(sum(_pnl(t) for t in trades if _pnl(t) <= 0))
                pf = gp / gl if gl > 0 else 0
                total = sum(_pnl(t) for t in trades)
                total_gross = sum(t.pnl_pct or 0 for t in trades)

                entries.append(AgentsLeaderboardEntry(
                    name=name,
                    status="running" if agent_info["enabled"] else "paused",
                    win_rate=round(wr, 1), profit_factor=round(pf, 3),
                    total_pnl_pct=round(total_gross, 2),
                    total_trades=len(trades),
                    net_win_rate=round(wr, 1),
                    net_profit_factor=round(pf, 3),
                    total_net_pnl_pct=round(total, 2),
                    balance=round(acc.balance, 2) if acc else 100_000,
                ))
            except Exception as e:
                entries.append(AgentsLeaderboardEntry(
                    name=name, status="idle",
                    win_rate=0, profit_factor=0, total_pnl_pct=0,
                    total_trades=0, net_win_rate=0, net_profit_factor=0,
                    total_net_pnl_pct=0,
                ))

    # Marca o melhor
    best = max(entries, key=lambda e: e.net_profit_factor, default=None)
    for e in entries:
        if best and e.name == best.name and e.net_profit_factor > 0:
            e.best = True

    return AgentsLeaderboardOut(agents=entries)
