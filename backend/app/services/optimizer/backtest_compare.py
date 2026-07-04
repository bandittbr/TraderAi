"""
Fase 8 — Backtest Comparativo V5 vs V6
Compara performance usando pesos padrão (V5) vs pesos adaptativos (V6)
a partir do signal_history real. Tudo determinístico.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome
from app.services.optimizer.criterion_performance import _compute_metrics, CRITERION_CANONICAL
from app.services.optimizer.weight_engine import weight_engine, DEFAULT_WEIGHT
from app.schemas.optimizer import BacktestComparisonResponse

logger = logging.getLogger(__name__)


class BacktestCompareEngine:
    """
    Simula performance V5 vs V6 sobre o histórico de sinais.
    V5: todos os critérios com peso 1 (score simples).
    V6: critérios com pesos adaptativos do weight_engine.
    """

    async def compare(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = 90,
    ) -> BacktestComparisonResponse:
        rows = await self._load_resolved_signals(symbol, lookback_days)
        if not rows:
            return BacktestComparisonResponse(
                symbol=symbol, lookback_days=lookback_days,
                v5_win_rate=None, v5_profit_factor=None, v5_sharpe=None,
                v5_drawdown=None, v5_expectancy=None, v5_signals=0,
                v6_win_rate=None, v6_profit_factor=None, v6_sharpe=None,
                v6_drawdown=None, v6_expectancy=None, v6_signals=0,
                improvement_wr=None, improvement_pf=None,
                computed_at=datetime.utcnow(),
            )

        weights = await weight_engine.load_weights()

        # Classificar sinais por estratégia
        # V5: usa confidence original (raw_score se disponível)
        # V6: usa weighted_score se disponível, senão recalcula

        v5_rows = []
        v6_rows = []

        for row in rows:
            # V5 inclui todos os sinais resolvidos como baseline
            v5_rows.append(row)

            # V6 filtra sinais com weighted_score >= threshold (simula filtro por qualidade)
            if row.weighted_score is not None:
                if row.weighted_score >= row.raw_score:  # V6 confirma ou supera V5
                    v6_rows.append(row)
            else:
                # Sem dado V6 ainda — recalcular com pesos atuais
                if row.criteria_met:
                    try:
                        clist   = json.loads(row.criteria_met)
                        met_w   = sum(
                            weights.get(CRITERION_CANONICAL.get(c, c), DEFAULT_WEIGHT)
                            for c in clist
                        )
                        raw_w   = len(clist) * DEFAULT_WEIGHT
                        if met_w >= raw_w * 0.9:   # V6 dentro de 10% do V5 mínimo
                            v6_rows.append(row)
                    except (json.JSONDecodeError, TypeError):
                        v6_rows.append(row)
                else:
                    v6_rows.append(row)

        v5_m = _compute_metrics(v5_rows)
        v6_m = _compute_metrics(v6_rows)

        improvement_wr = (
            round(v6_m["win_rate"] - v5_m["win_rate"], 2)
            if v5_m["win_rate"] and v6_m["win_rate"] else None
        )
        improvement_pf = (
            round(v6_m["profit_factor"] - v5_m["profit_factor"], 3)
            if v5_m["profit_factor"] and v6_m["profit_factor"] else None
        )

        return BacktestComparisonResponse(
            symbol          = symbol,
            lookback_days   = lookback_days,
            v5_win_rate     = v5_m["win_rate"]      or None,
            v5_profit_factor= v5_m["profit_factor"] or None,
            v5_sharpe       = v5_m["sharpe"]        or None,
            v5_drawdown     = v5_m["max_drawdown"]  or None,
            v5_expectancy   = v5_m["expectancy"]    or None,
            v5_signals      = v5_m["resolved"],
            v6_win_rate     = v6_m["win_rate"]      or None,
            v6_profit_factor= v6_m["profit_factor"] or None,
            v6_sharpe       = v6_m["sharpe"]        or None,
            v6_drawdown     = v6_m["max_drawdown"]  or None,
            v6_expectancy   = v6_m["expectancy"]    or None,
            v6_signals      = v6_m["resolved"],
            improvement_wr  = improvement_wr,
            improvement_pf  = improvement_pf,
            computed_at     = datetime.utcnow(),
        )

    async def _load_resolved_signals(self, symbol, lookback_days):
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        try:
            async with AsyncSessionLocal() as db:
                q = select(SignalHistory).where(
                    SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                    SignalHistory.emitted_at >= cutoff,
                    SignalHistory.pnl_pct.isnot(None),
                )
                if symbol:
                    q = q.where(SignalHistory.symbol == symbol)
                result = await db.execute(q.order_by(SignalHistory.emitted_at))
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[backtest_compare] load: %s", e)
            return []


backtest_compare_engine = BacktestCompareEngine()
