"""
Fase 8 — Regime Performance Analyzer
Separa performance de cada critério por regime de mercado.
Determina quais critérios funcionam em cada regime e quais devem ser evitados.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome, MarketRegimeType
from app.services.optimizer.criterion_performance import (
    CRITERION_CANONICAL, ALL_CANONICAL, _compute_metrics
)

logger = logging.getLogger(__name__)

REGIMES = ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY"]
MIN_REGIME_SAMPLE = 3


@dataclass
class RegimeCriterionStats:
    """Performance de um critério em um regime específico."""
    criterion:     str
    regime:        str
    sample_size:   int   = 0
    win_rate:      float = 0.0
    profit_factor: float = 0.0
    expectancy:    float = 0.0
    recommended:   bool  = False  # True se supera baseline do regime
    avoid:         bool  = False  # True se pf < 0.8 ou wr < 40


@dataclass
class RegimeReport:
    """Relatório completo por regime."""
    regimes:    dict[str, RegimeData] = field(default_factory=dict)
    total_rows: int = 0


@dataclass
class RegimeData:
    """Dados de um regime específico."""
    regime:           str
    total_signals:    int              = 0
    baseline_wr:      float            = 0.0
    baseline_pf:      float            = 0.0
    criteria_stats:   list[RegimeCriterionStats] = field(default_factory=list)
    best_criteria:    list[str]        = field(default_factory=list)
    avoid_criteria:   list[str]        = field(default_factory=list)


class RegimePerformanceAnalyzer:
    """Analisa qual critério performa melhor em cada regime."""

    async def compute(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = 90,
    ) -> RegimeReport:
        rows = await self._load_resolved_signals(symbol, lookback_days)
        if not rows:
            return RegimeReport()

        # Separar por regime
        regime_map: dict[str, list] = {r: [] for r in REGIMES}
        regime_map["UNKNOWN"] = []
        for row in rows:
            reg_val = str(row.regime.value) if row.regime else "UNKNOWN"
            if reg_val in regime_map:
                regime_map[reg_val].append(row)
            else:
                regime_map.setdefault(reg_val, []).append(row)

        report = RegimeReport(total_rows=len(rows))

        for regime_name, regime_rows in regime_map.items():
            if not regime_rows:
                continue

            baseline = _compute_metrics(regime_rows)
            data = RegimeData(
                regime        = regime_name,
                total_signals = baseline["resolved"],
                baseline_wr   = baseline["win_rate"],
                baseline_pf   = baseline["profit_factor"],
            )

            # Critérios neste regime
            criterion_rows: dict[str, list] = {c: [] for c in ALL_CANONICAL}
            for row in regime_rows:
                if not row.criteria_met:
                    continue
                try:
                    clist = json.loads(row.criteria_met)
                except (json.JSONDecodeError, TypeError):
                    continue
                seen: set[str] = set()
                for c in clist:
                    can = CRITERION_CANONICAL.get(c)
                    if can and can not in seen:
                        seen.add(can)
                        criterion_rows[can].append(row)

            crit_stats: list[RegimeCriterionStats] = []
            for canonical, c_rows in criterion_rows.items():
                m = _compute_metrics(c_rows)
                if m["resolved"] < MIN_REGIME_SAMPLE:
                    continue
                recommended = (
                    m["win_rate"] >= baseline["win_rate"] and
                    m["profit_factor"] >= baseline["profit_factor"]
                )
                avoid = m["profit_factor"] < 0.8 or m["win_rate"] < 35.0
                crit_stats.append(RegimeCriterionStats(
                    criterion     = canonical,
                    regime        = regime_name,
                    sample_size   = m["resolved"],
                    win_rate      = m["win_rate"],
                    profit_factor = m["profit_factor"],
                    expectancy    = m["expectancy"],
                    recommended   = recommended,
                    avoid         = avoid,
                ))

            crit_stats.sort(key=lambda s: s.profit_factor * (s.win_rate / 100), reverse=True)
            data.criteria_stats  = crit_stats
            data.best_criteria   = [s.criterion for s in crit_stats if s.recommended][:5]
            data.avoid_criteria  = [s.criterion for s in crit_stats if s.avoid][:5]
            report.regimes[regime_name] = data

        return report

    async def _load_resolved_signals(self, symbol, lookback_days):
        from datetime import datetime, timedelta
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
            logger.error("[regime_perf] load: %s", e)
            return []


regime_performance_analyzer = RegimePerformanceAnalyzer()
