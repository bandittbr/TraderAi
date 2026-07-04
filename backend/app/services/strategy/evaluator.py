"""
Fase 11 — Strategy Evaluator
Executa backtests determinísticos sobre signal_history.
Para cada estratégia, filtra trades que satisfazem as entry_rules e calcula métricas.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome

logger = logging.getLogger(__name__)

LOOKBACK_DAYS   = 90
MIN_TRADES      = 5
SCORE_WR_W      = 0.40
SCORE_PF_W      = 0.30
SCORE_SHARPE_W  = 0.15
SCORE_CALMAR_W  = 0.15


@dataclass
class BacktestResult:
    strategy_key:    str
    symbol:          Optional[str]
    period_days:     int
    n_trades:        int
    win_rate:        float
    profit_factor:   float
    sharpe:          float
    calmar:          float
    expectancy:      float
    max_drawdown:    float
    avg_win_pct:     float
    avg_loss_pct:    float
    total_return_pct: float
    strategy_score:  float
    executed_at:     datetime


class StrategyEvaluator:
    """
    Avalia estratégias contra histórico de sinais.
    Determinístico — sem IA.
    """

    async def evaluate(
        self,
        entry_rules:  dict,
        exit_rules:   dict,
        risk_rules:   dict,
        strategy_key: str,
        symbol:       Optional[str] = None,
        period_days:  int           = LOOKBACK_DAYS,
    ) -> BacktestResult:
        """Executa backtest e retorna métricas."""
        rows = await self._load_matching_trades(entry_rules, risk_rules, symbol, period_days)
        return _compute_metrics(rows, strategy_key, symbol, period_days, exit_rules)

    async def _load_matching_trades(
        self,
        entry_rules: dict,
        risk_rules:  dict,
        symbol:      Optional[str],
        period_days: int,
    ) -> list:
        """Carrega trades históricos que satisfazem as entry_rules."""
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        allowed_regimes = set(risk_rules.get("regime_filter", []))

        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(SignalHistory)
                    .where(
                        SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                        SignalHistory.pnl_pct.isnot(None),
                        SignalHistory.emitted_at >= cutoff,
                    )
                    .order_by(SignalHistory.emitted_at)
                )
                if symbol:
                    q = q.where(SignalHistory.symbol == symbol)
                result = await db.execute(q)
                rows   = list(result.scalars().all())

            # Filtrar por regime
            if allowed_regimes and "ALL" not in allowed_regimes:
                rows = [r for r in rows if getattr(r, "regime", None) in allowed_regimes]

            # Filtrar por criteria_met: contar quantos critérios da estratégia estão presentes
            min_conf = risk_rules.get("min_confluence", 2)
            strategy_criteria = _active_criteria(entry_rules)
            if strategy_criteria:
                rows = _filter_by_criteria(rows, strategy_criteria, min_conf)

            return rows
        except Exception as exc:
            logger.error("[evaluator] _load: %s", exc)
            return []

    async def persist(self, result: BacktestResult, strategy_id: int) -> None:
        """Persiste resultado no banco."""
        try:
            from app.models.strategies import StrategyBacktest
            async with AsyncSessionLocal() as db:
                obj = StrategyBacktest(
                    strategy_id      = strategy_id,
                    symbol           = result.symbol,
                    period_days      = result.period_days,
                    n_trades         = result.n_trades,
                    win_rate         = result.win_rate,
                    profit_factor    = result.profit_factor,
                    sharpe           = result.sharpe,
                    calmar           = result.calmar,
                    expectancy       = result.expectancy,
                    max_drawdown     = result.max_drawdown,
                    avg_win_pct      = result.avg_win_pct,
                    avg_loss_pct     = result.avg_loss_pct,
                    total_return_pct = result.total_return_pct,
                    strategy_score   = result.strategy_score,
                    executed_at      = result.executed_at,
                )
                db.add(obj)
                await db.commit()
        except Exception as exc:
            logger.error("[evaluator] persist: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _active_criteria(entry_rules: dict) -> list[str]:
    """Retorna lista de critérios ativos na estratégia."""
    boolean_keys = {
        "rsi_oversold", "rsi_overbought", "macd_bullish", "macd_bearish",
        "ema_trend_up", "ema_trend_down", "bos_detected", "choch_detected",
        "fvg_present", "sweep_present", "hvn_support", "fear_extreme",
        "greed_extreme", "funding_negative", "oi_increasing", "context_bullish",
    }
    return [k for k, v in entry_rules.items() if k in boolean_keys and v is True]


def _filter_by_criteria(rows: list, strategy_criteria: list[str], min_conf: int) -> list:
    """Filtra trades onde pelo menos min_conf critérios da estratégia estão no criteria_met."""
    # Mapeamento de critério da estratégia → campos da SignalHistory
    FIELD_MAP = {
        "bos_detected":    lambda r: bool(getattr(r, "had_sweep", False)),
        "fvg_present":     lambda r: bool(getattr(r, "had_fvg",   False)),
        "sweep_present":   lambda r: bool(getattr(r, "had_sweep", False)),
        "hvn_support":     lambda r: bool(getattr(r, "had_hvn",   False)),
    }

    result = []
    for r in rows:
        # Verificar via criteria_met JSON
        crit_met: set[str] = set()
        if r.criteria_met:
            try:
                clist = json.loads(r.criteria_met)
                # Mapear criteria_met para strategy criteria
                for sc in strategy_criteria:
                    if sc in clist:
                        crit_met.add(sc)
                    elif sc in FIELD_MAP and FIELD_MAP[sc](r):
                        crit_met.add(sc)
                    elif _criterion_from_fields(sc, r):
                        crit_met.add(sc)
            except Exception:
                pass
        else:
            for sc in strategy_criteria:
                if sc in FIELD_MAP and FIELD_MAP[sc](r):
                    crit_met.add(sc)
                elif _criterion_from_fields(sc, r):
                    crit_met.add(sc)

        if len(crit_met) >= min_conf:
            result.append(r)

    return result


def _criterion_from_fields(criterion: str, row) -> bool:
    """Verifica critérios via campos diretos da SignalHistory."""
    if criterion == "fear_extreme":
        fg = getattr(row, "fear_greed_value", None)
        return fg is not None and fg < 25
    if criterion == "greed_extreme":
        fg = getattr(row, "fear_greed_value", None)
        return fg is not None and fg > 75
    if criterion == "context_bullish":
        cs = getattr(row, "context_score", None)
        return cs is not None and cs >= 60
    return False


def _compute_metrics(
    rows:         list,
    strategy_key: str,
    symbol:       Optional[str],
    period_days:  int,
    exit_rules:   dict,
) -> BacktestResult:
    """Calcula todas as métricas de performance."""
    n = len(rows)
    if n < MIN_TRADES:
        return BacktestResult(
            strategy_key=strategy_key, symbol=symbol, period_days=period_days,
            n_trades=n, win_rate=0.0, profit_factor=0.0, sharpe=0.0,
            calmar=0.0, expectancy=0.0, max_drawdown=0.0,
            avg_win_pct=0.0, avg_loss_pct=0.0, total_return_pct=0.0,
            strategy_score=0.0, executed_at=datetime.utcnow(),
        )

    wins   = [r for r in rows if r.outcome == SignalOutcome.WIN]
    losses = [r for r in rows if r.outcome == SignalOutcome.LOSS]
    wr     = len(wins) / n * 100.0
    avg_win  = sum(r.pnl_pct for r in wins)   / len(wins)   if wins   else 0.0
    avg_loss = abs(sum(r.pnl_pct for r in losses) / len(losses)) if losses else 1.0
    pf       = avg_win / avg_loss if avg_loss > 0 else 0.0
    exp      = sum(r.pnl_pct for r in rows) / n
    total    = sum(r.pnl_pct for r in rows)

    # Max Drawdown sobre equity curve
    equity = 0.0; peak = 0.0; max_dd = 0.0
    for r in sorted(rows, key=lambda x: x.emitted_at):
        equity += r.pnl_pct
        if equity > peak: peak = equity
        dd = peak - equity
        if dd > max_dd: max_dd = dd

    # Sharpe (diário normalizado)
    pnls  = [r.pnl_pct for r in rows]
    mean  = sum(pnls) / n
    std   = math.sqrt(sum((p - mean) ** 2 for p in pnls) / n) if n > 1 else 1.0
    sharpe = mean / std if std > 0 else 0.0

    # Calmar = total_return / max_drawdown
    calmar = total / max_dd if max_dd > 0 else 0.0

    score = _compute_score(wr, pf, sharpe, calmar)

    return BacktestResult(
        strategy_key     = strategy_key,
        symbol           = symbol,
        period_days      = period_days,
        n_trades         = n,
        win_rate         = round(wr, 2),
        profit_factor    = round(pf, 3),
        sharpe           = round(sharpe, 3),
        calmar           = round(calmar, 3),
        expectancy       = round(exp, 3),
        max_drawdown     = round(max_dd, 2),
        avg_win_pct      = round(avg_win, 3),
        avg_loss_pct     = round(avg_loss, 3),
        total_return_pct = round(total, 2),
        strategy_score   = score,
        executed_at      = datetime.utcnow(),
    )


def _compute_score(wr: float, pf: float, sharpe: float, calmar: float) -> float:
    """Score composto 0-100."""
    wr_norm     = min(wr, 100.0) * SCORE_WR_W
    pf_norm     = min(pf / 3.0, 1.0) * 100.0 * SCORE_PF_W
    sh_norm     = min(max(sharpe, 0) / 3.0, 1.0) * 100.0 * SCORE_SHARPE_W
    cal_norm    = min(max(calmar, 0) / 3.0, 1.0) * 100.0 * SCORE_CALMAR_W
    return round(wr_norm + pf_norm + sh_norm + cal_norm, 2)


# ── Singleton ─────────────────────────────────────────────────────────────────

strategy_evaluator = StrategyEvaluator()
