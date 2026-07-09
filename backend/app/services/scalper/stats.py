"""
Scalper Stats Engine (Fase 13)
Calcula métricas de performance do Scalper independentemente.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from app.database import AsyncSessionLocal
from app.models.scalper import ScalperTrade, ScalperAccount, ScalperRiskDaily


async def get_scalper_stats(days: int = 30) -> dict:
    """Retorna estatísticas completas do Scalper Engine."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    async with AsyncSessionLocal() as session:
        # Todos os trades fechados no período
        result = await session.execute(
            select(ScalperTrade).where(
                ScalperTrade.status   == "CLOSED",
                ScalperTrade.closed_at >= cutoff,
            )
        )
        trades = list(result.scalars().all())

        # Trades abertos agora
        open_result = await session.execute(
            select(ScalperTrade).where(ScalperTrade.status == "OPEN")
        )
        open_trades = list(open_result.scalars().all())

        # Conta
        acc = await session.scalar(select(ScalperAccount))

    if not trades:
        return {
            "period_days":     days,
            "total_trades":    0,
            "open_trades":     len(open_trades),
            "win_rate":        0.0,
            "profit_factor":   0.0,
            "total_pnl_usd":   0.0,
            "total_pnl_pct":   0.0,
            "avg_trade_pnl":   0.0,
            "avg_win_pct":     0.0,
            "avg_loss_pct":    0.0,
            "max_win_pct":     0.0,
            "max_loss_pct":    0.0,
            "avg_duration_min":0.0,
            "balance":         acc.balance if acc else 10_000.0,
            "initial_balance": acc.initial_balance if acc else 10_000.0,
            "peak_balance":    acc.peak_balance if acc else 10_000.0,
            "by_side":         {},
            "by_symbol":       {},
            "by_reason":       {},
        }

    # ── Gross (PnL bruto, usado historicamente) ──
    wins   = [t for t in trades if (t.pnl or 0) > 0]
    losses = [t for t in trades if (t.pnl or 0) <= 0]

    gross_profit = sum(t.pnl for t in wins)   if wins   else 0.0
    gross_loss   = abs(sum(t.pnl for t in losses)) if losses else 0.0
    pf           = round(gross_profit / gross_loss, 3) if gross_loss > 0 else 0.0

    # ── Net (fee-ajustado, V7.11) ──
    _use_net = lambda t: (t.net_pnl_pct if t.net_pnl_pct is not None else t.pnl_pct or 0)
    net_wins   = [t for t in trades if _use_net(t) > 0]
    net_losses = [t for t in trades if _use_net(t) <= 0]
    net_gp = sum(_use_net(t) for t in net_wins)
    net_gl = abs(sum(_use_net(t) for t in net_losses)) if net_losses else 0.0
    net_pf = round(net_gp / net_gl, 3) if net_gl > 0 else 0.0

    # By side
    by_side = {}
    for side in ("LONG", "SHORT"):
        sub = [t for t in trades if t.trade_side == side]
        if not sub:
            continue
        sub_wins   = [t for t in sub if (t.pnl or 0) > 0]
        sub_losses = [t for t in sub if (t.pnl or 0) <= 0]
        gp = sum(t.pnl for t in sub_wins)   if sub_wins   else 0.0
        gl = abs(sum(t.pnl for t in sub_losses)) if sub_losses else 0.0
        by_side[side] = {
            "trades":        len(sub),
            "wins":          len(sub_wins),
            "losses":        len(sub_losses),
            "win_rate":      round(len(sub_wins) / len(sub) * 100, 1),
            "profit_factor": round(gp / gl, 3) if gl > 0 else 0.0,
            "total_pnl_usd": round(sum(t.pnl or 0 for t in sub), 4),
        }

    # By symbol
    by_symbol: dict[str, dict] = {}
    for t in trades:
        s = t.symbol
        if s not in by_symbol:
            by_symbol[s] = {"trades": 0, "pnl": 0.0, "wins": 0}
        by_symbol[s]["trades"] += 1
        by_symbol[s]["pnl"]    += t.pnl or 0
        if (t.pnl or 0) > 0:
            by_symbol[s]["wins"] += 1
    for v in by_symbol.values():
        v["pnl"]      = round(v["pnl"], 4)
        v["win_rate"] = round(v["wins"] / v["trades"] * 100, 1)

    # By close reason
    by_reason: dict[str, int] = {}
    for t in trades:
        r = t.close_reason or "UNKNOWN"
        by_reason[r] = by_reason.get(r, 0) + 1

    durations = [t.duration_minutes for t in trades if t.duration_minutes is not None]

    return {
        "period_days":      days,
        "total_trades":     len(trades),
        "open_trades":      len(open_trades),
        "win_rate":         round(len(wins) / len(trades) * 100, 1),
        "profit_factor":    pf,
        "total_pnl_usd":    round(sum(t.pnl or 0 for t in trades), 4),
        "total_pnl_pct":    round(sum(t.pnl_pct or 0 for t in trades), 4),
        "avg_trade_pnl":    round(sum(t.pnl or 0 for t in trades) / len(trades), 4),
        "avg_win_pct":      round(sum(t.pnl_pct or 0 for t in wins)   / len(wins)   if wins   else 0, 3),
        "avg_loss_pct":     round(sum(t.pnl_pct or 0 for t in losses) / len(losses) if losses else 0, 3),
        "max_win_pct":      round(max((t.pnl_pct or 0) for t in wins)   if wins   else 0, 3),
        "max_loss_pct":     round(min((t.pnl_pct or 0) for t in losses) if losses else 0, 3),
        # V7.11 — Net (fee-ajustado)
        "net_win_rate":     round(len(net_wins) / len(trades) * 100, 1),
        "net_profit_factor": net_pf,
        "total_net_pnl_pct": round(sum(_use_net(t) for t in trades), 4),
        "avg_duration_min": round(sum(durations) / len(durations) if durations else 0, 1),
        "balance":          round(acc.balance if acc else 10_000.0, 2),
        "initial_balance":  round(acc.initial_balance if acc else 10_000.0, 2),
        "peak_balance":     round(acc.peak_balance if acc else 10_000.0, 2),
        "by_side":          by_side,
        "by_symbol":        by_symbol,
        "by_reason":        by_reason,
    }
