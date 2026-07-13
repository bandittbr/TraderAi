"""
Worker Agent — API Endpoints (V7)
Agente 24/7 multi-timeframe com alavancagem adaptativa.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Query
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models.worker import WorkerAccount, WorkerTrade, WorkerRiskDaily
from app.schemas.worker import (
    WorkerAccountOut, WorkerTradeOut, WorkerRiskOut,
    WorkerStatsOut, WorkerDebugOut,
    AgentLeaderboardOut, AgentLeaderboardEntry,
)
from app.services.worker.trade_engine import worker_engine, INITIAL_BALANCE
from app.services.worker.risk_manager import worker_risk

# Import agents for leaderboard
from app.models.scalper import ScalperTrade, ScalperAccount
from app.models.paper_trading import PaperTrade, PaperAccount
from app.models.groq_agent import GroqTrade

router = APIRouter()


# ── GET /worker/account ──────────────────────────────────────────────────────
@router.get("/account", response_model=WorkerAccountOut)
async def get_worker_account():
    """Saldo e patrimônio da conta do Worker."""
    async with AsyncSessionLocal() as session:
        acc = await session.scalar(select(WorkerAccount))
        if acc is None:
            acc = WorkerAccount(
                balance=INITIAL_BALANCE, initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            session.add(acc)
            await session.commit()
            await session.refresh(acc)
        return WorkerAccountOut.model_validate(acc)


# ── GET /worker/trades ───────────────────────────────────────────────────────
@router.get("/trades", response_model=list[WorkerTradeOut])
async def get_worker_trades(
    status: str | None = Query(None, description="OPEN ou CLOSED"),
    limit:  int        = Query(50, ge=1, le=500),
):
    """Lista trades do Worker."""
    async with AsyncSessionLocal() as session:
        q = select(WorkerTrade).order_by(desc(WorkerTrade.opened_at)).limit(limit)
        if status:
            q = q.where(WorkerTrade.status == status.upper())
        result = await session.execute(q)
        trades = list(result.scalars().all())
    return [WorkerTradeOut.model_validate(t) for t in trades]


# ── GET /worker/stats ────────────────────────────────────────────────────────
@router.get("/stats", response_model=WorkerStatsOut)
async def get_worker_stats(days: int = Query(30, ge=1, le=365)):
    """Estatísticas do Worker Agent."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(WorkerTrade).where(
                WorkerTrade.status == "CLOSED",
                WorkerTrade.closed_at >= cutoff,
            )
        )
        trades = list(result.scalars().all())

        open_result = await session.execute(
            select(WorkerTrade).where(WorkerTrade.status == "OPEN")
        )
        open_trades = list(open_result.scalars().all())

        acc = await session.scalar(select(WorkerAccount))

    if not trades:
        return WorkerStatsOut(
            period_days=days, total_trades=0, open_trades=len(open_trades),
            win_rate=0, profit_factor=0, total_pnl_usd=0, total_pnl_pct=0,
            avg_trade_pnl=0, avg_win_pct=0, avg_loss_pct=0,
            max_win_pct=0, max_loss_pct=0,
            net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            avg_duration_min=0,
            balance=acc.balance if acc else INITIAL_BALANCE,
            initial_balance=acc.initial_balance if acc else INITIAL_BALANCE,
            peak_balance=acc.peak_balance if acc else INITIAL_BALANCE,
            current_leverage=1,
        )

    def _pnl(t):
        return t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0

    wins   = [t for t in trades if _pnl(t) > 0]
    losses = [t for t in trades if _pnl(t) <= 0]
    wr     = len(wins) / len(trades) * 100 if trades else 0

    gross_profit = sum(_pnl(t) for t in wins) if wins else 0
    gross_loss   = abs(sum(_pnl(t) for t in losses)) if losses else 0
    pf = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

    total_pnl_pct = sum(_pnl(t) for t in trades)
    total_pnl_usd = sum(t.pnl or 0 for t in trades)

    avg_win  = sum(_pnl(t) for t in wins)   / len(wins)   if wins   else 0
    avg_loss = sum(abs(_pnl(t)) for t in losses) / len(losses) if losses else 0

    max_win  = max((_pnl(t) for t in wins),   default=0)
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

    # Net
    net_wins = [t for t in trades if _pnl(t) > 0]
    net_wr = len(net_wins) / len(trades) * 100 if trades else 0
    net_gp = sum(_pnl(t) for t in net_wins) if net_wins else 0
    net_gl = abs(sum(_pnl(t) for t in trades if _pnl(t) <= 0)) if losses else 0
    net_pf = net_gp / net_gl if net_gl > 0 else 0

    return WorkerStatsOut(
        period_days=days, total_trades=len(trades),
        open_trades=len(open_trades),
        win_rate=round(wr, 1), profit_factor=round(pf, 3),
        total_pnl_usd=round(total_pnl_usd, 4),
        total_pnl_pct=round(total_pnl_pct, 4),
        avg_trade_pnl=round(total_pnl_usd / len(trades), 4) if trades else 0,
        avg_win_pct=round(avg_win, 3), avg_loss_pct=round(avg_loss, 3),
        max_win_pct=round(max_win, 3), max_loss_pct=round(max_loss, 3),
        net_win_rate=round(net_wr, 1), net_profit_factor=round(net_pf, 3),
        total_net_pnl_pct=round(sum(_pnl(t) for t in trades), 4),
        avg_duration_min=round(sum(durations) / len(durations), 1) if durations else 0,
        balance=round(acc.balance, 2) if acc else INITIAL_BALANCE,
        initial_balance=round(acc.initial_balance, 2) if acc else INITIAL_BALANCE,
        peak_balance=round(acc.peak_balance, 2) if acc else INITIAL_BALANCE,
        current_leverage=1,
        by_symbol=by_sym, by_reason=by_reason,
    )


# ── GET /worker/debug ────────────────────────────────────────────────────────
@router.get("/debug", response_model=WorkerDebugOut)
async def get_worker_debug():
    """Diagnóstico completo do Worker Agent."""
    async with AsyncSessionLocal() as session:
        acc = await session.scalar(select(WorkerAccount))
        if acc is None:
            acc_placeholder = WorkerAccount(
                balance=INITIAL_BALANCE, initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            account_out = WorkerAccountOut.model_validate(acc_placeholder)
        else:
            account_out = WorkerAccountOut.model_validate(acc)

        open_trades_q = await session.execute(
            select(WorkerTrade).where(WorkerTrade.status == "OPEN")
        )
        open_trades = [WorkerTradeOut.model_validate(t) for t in open_trades_q.scalars().all()]

        risk_out = None
        try:
            row = await session.scalar(
                select(WorkerRiskDaily).where(WorkerRiskDaily.date == date.today().isoformat())
            )
            if row:
                risk_out = WorkerRiskOut.model_validate(row)
        except Exception:
            pass

    return WorkerDebugOut(account=account_out, open_trades=open_trades, risk_today=risk_out)


# ── GET /agents/leaderboard ──────────────────────────────────────────────────
@router.get("/leaderboard", response_model=AgentLeaderboardOut)
async def get_agent_leaderboard(days: int = Query(30, ge=1, le=365)):
    """Leaderboard comparativo de todos os agentes."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    agents = []

    async with AsyncSessionLocal() as session:
        # ── Worker ──
        try:
            wt = await session.execute(
                select(WorkerTrade).where(
                    WorkerTrade.status == "CLOSED",
                    WorkerTrade.closed_at >= cutoff,
                )
            )
            worker_trades = list(wt.scalars().all())
            w_pnl = lambda t: t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0
            w_wins = [t for t in worker_trades if w_pnl(t) > 0]
            w_wr = len(w_wins) / len(worker_trades) * 100 if worker_trades else 0
            w_gp = sum(w_pnl(t) for t in w_wins)
            w_gl = abs(sum(w_pnl(t) for t in worker_trades if w_pnl(t) <= 0))
            w_pf = w_gp / w_gl if w_gl > 0 else 0
            w_total = sum(w_pnl(t) for t in worker_trades)
            # gross pnl_pct para total_pnl_pct
            w_total_gross = sum(t.pnl_pct or 0 for t in worker_trades)
            agents.append(AgentLeaderboardEntry(
                name="Worker", status="running",
                win_rate=round(w_wr, 1), profit_factor=round(w_pf, 3),
                total_pnl_pct=round(w_total_gross, 2),
                total_trades=len(worker_trades),
                net_win_rate=round(w_wr, 1), net_profit_factor=round(w_pf, 3),
                total_net_pnl_pct=round(w_total, 2),
            ))
        except Exception as e:
            agents.append(AgentLeaderboardEntry(
                name="Worker", status="idle",
                win_rate=0, profit_factor=0, total_pnl_pct=0, total_trades=0,
                net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            ))

        # ── Scalper ──
        try:
            st = await session.execute(
                select(ScalperTrade).where(
                    ScalperTrade.status == "CLOSED",
                    ScalperTrade.closed_at >= cutoff,
                )
            )
            scalper_trades = list(st.scalars().all())
            s_pnl = lambda t: t.net_pnl_pct if hasattr(t, 'net_pnl_pct') and t.net_pnl_pct is not None else t.pnl_pct or 0
            s_wins = [t for t in scalper_trades if s_pnl(t) > 0]
            s_wr = len(s_wins) / len(scalper_trades) * 100 if scalper_trades else 0
            s_gp = sum(s_pnl(t) for t in s_wins)
            s_gl = abs(sum(s_pnl(t) for t in scalper_trades if s_pnl(t) <= 0))
            s_pf = s_gp / s_gl if s_gl > 0 else 0
            s_total = sum(s_pnl(t) for t in scalper_trades)
            s_total_gross = sum(t.pnl_pct or 0 for t in scalper_trades)
            agents.append(AgentLeaderboardEntry(
                name="Scalper", status="running",
                win_rate=round(s_wr, 1), profit_factor=round(s_pf, 3),
                total_pnl_pct=round(s_total_gross, 2),
                total_trades=len(scalper_trades),
                net_win_rate=round(s_wr, 1), net_profit_factor=round(s_pf, 3),
                total_net_pnl_pct=round(s_total, 2),
            ))
        except Exception as e:
            agents.append(AgentLeaderboardEntry(
                name="Scalper", status="idle",
                win_rate=0, profit_factor=0, total_pnl_pct=0, total_trades=0,
                net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            ))

        # ── Paper ──
        try:
            pt = await session.execute(
                select(PaperTrade).where(
                    PaperTrade.status == "CLOSED",
                    PaperTrade.closed_at >= cutoff,
                )
            )
            paper_trades = list(pt.scalars().all())
            p_pnl = lambda t: t.net_pnl_percent if hasattr(t, 'net_pnl_percent') and t.net_pnl_percent is not None else t.pnl_percent or 0
            p_wins = [t for t in paper_trades if p_pnl(t) > 0]
            p_wr = len(p_wins) / len(paper_trades) * 100 if paper_trades else 0
            p_gp = sum(p_pnl(t) for t in p_wins)
            p_gl = abs(sum(p_pnl(t) for t in paper_trades if p_pnl(t) <= 0))
            p_pf = p_gp / p_gl if p_gl > 0 else 0
            p_total = sum(p_pnl(t) for t in paper_trades)
            p_total_gross = sum(t.pnl_percent or 0 for t in paper_trades)
            agents.append(AgentLeaderboardEntry(
                name="Paper", status="running",
                win_rate=round(p_wr, 1), profit_factor=round(p_pf, 3),
                total_pnl_pct=round(p_total_gross, 2),
                total_trades=len(paper_trades),
                net_win_rate=round(p_wr, 1), net_profit_factor=round(p_pf, 3),
                total_net_pnl_pct=round(p_total, 2),
            ))
        except Exception as e:
            agents.append(AgentLeaderboardEntry(
                name="Paper", status="idle",
                win_rate=0, profit_factor=0, total_pnl_pct=0, total_trades=0,
                net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            ))

        # ── Groq ──
        try:
            gt = await session.execute(
                select(GroqTrade).where(
                    GroqTrade.status == "CLOSED",
                    GroqTrade.closed_at >= cutoff,
                )
            )
            groq_trades = list(gt.scalars().all())
            g_pnl = lambda t: t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0
            g_wins = [t for t in groq_trades if g_pnl(t) > 0]
            g_wr = len(g_wins) / len(groq_trades) * 100 if groq_trades else 0
            g_gp = sum(g_pnl(t) for t in g_wins)
            g_gl = abs(sum(g_pnl(t) for t in groq_trades if g_pnl(t) <= 0))
            g_pf = g_gp / g_gl if g_gl > 0 else 0
            g_total = sum(g_pnl(t) for t in groq_trades)
            g_total_gross = sum(t.pnl_pct or 0 for t in groq_trades)
            agents.append(AgentLeaderboardEntry(
                name="Groq", status="running",
                win_rate=round(g_wr, 1), profit_factor=round(g_pf, 3),
                total_pnl_pct=round(g_total_gross, 2),
                total_trades=len(groq_trades),
                net_win_rate=round(g_wr, 1), net_profit_factor=round(g_pf, 3),
                total_net_pnl_pct=round(g_total, 2),
            ))
        except Exception as e:
            agents.append(AgentLeaderboardEntry(
                name="Groq", status="idle",
                win_rate=0, profit_factor=0, total_pnl_pct=0, total_trades=0,
                net_win_rate=0, net_profit_factor=0, total_net_pnl_pct=0,
            ))

    # Marca o melhor (net profit factor mais alto)
    best_agent = max(agents, key=lambda a: a.net_profit_factor, default=None)
    for a in agents:
        if best_agent and a.name == best_agent.name and a.net_profit_factor > 0:
            a.best = True

    return AgentLeaderboardOut(agents=agents)
