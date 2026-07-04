"""
Fase 8 — Combination Analyzer
Descobre automaticamente as top-N combinações de critérios mais lucrativas.
Tudo determinístico — sem IA, sem LLM.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from itertools import combinations
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome
from app.services.optimizer.criterion_performance import (
    CRITERION_CANONICAL, _compute_metrics
)

logger = logging.getLogger(__name__)

MIN_COMBO_SAMPLE = 8    # mínimo de trades para uma combinação ser válida
MAX_COMBO_SIZE   = 4    # máximo de critérios por combinação
TOP_N            = 50   # top combinações a retornar


@dataclass
class CombinationStats:
    """Performance de uma combinação específica de critérios."""
    criteria:      tuple[str, ...]
    criteria_key:  str        # "+".join(sorted)
    sample_size:   int        = 0
    wins:          int        = 0
    losses:        int        = 0
    win_rate:      float      = 0.0
    profit_factor: float      = 0.0
    expectancy:    float      = 0.0
    sharpe:        float      = 0.0
    max_drawdown:  float      = 0.0
    score:         float      = 0.0   # ranking score
    direction:     str        = "BOTH"  # BUY | SELL | BOTH


@dataclass
class CombinationReport:
    """Relatório de combinações."""
    top_buy:  list[CombinationStats] = field(default_factory=list)
    top_sell: list[CombinationStats] = field(default_factory=list)
    top_all:  list[CombinationStats] = field(default_factory=list)
    analyzed: int = 0
    valid:    int = 0


class CombinationAnalyzer:
    """Analisa combinações de critérios para encontrar as mais lucrativas."""

    async def compute(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = 90,
        top_n:         int           = TOP_N,
    ) -> CombinationReport:
        rows = await self._load_resolved_signals(symbol, lookback_days)
        if not rows:
            return CombinationReport()

        # Parsear critérios de cada sinal
        parsed: list[dict] = []
        for row in rows:
            if not row.criteria_met:
                continue
            try:
                clist = json.loads(row.criteria_met)
            except (json.JSONDecodeError, TypeError):
                continue
            # Canonicalizar
            canonicals = sorted(set(
                CRITERION_CANONICAL[c] for c in clist if c in CRITERION_CANONICAL
            ))
            if canonicals:
                parsed.append({
                    "row":      row,
                    "criteria": canonicals,
                    "signal":   str(row.signal.value) if row.signal else "NEUTRAL",
                })

        if not parsed:
            return CombinationReport()

        # Coletar todos os critérios únicos presentes
        all_criteria = sorted(set(
            c for p in parsed for c in p["criteria"]
        ))

        # Gerar e avaliar combinações
        combo_map: dict[str, list] = {}
        analyzed = 0
        for size in range(2, MAX_COMBO_SIZE + 1):
            for combo in combinations(all_criteria, size):
                key = "+".join(combo)
                matching = [
                    p["row"] for p in parsed
                    if all(c in p["criteria"] for c in combo)
                ]
                if len(matching) >= MIN_COMBO_SAMPLE:
                    combo_map[key] = (combo, matching)
                analyzed += 1

        valid = len(combo_map)
        if not combo_map:
            return CombinationReport(analyzed=analyzed, valid=0)

        # Calcular stats e ranking
        results: list[CombinationStats] = []
        for key, (combo, matching) in combo_map.items():
            m = _compute_metrics(matching)
            if m["resolved"] < MIN_COMBO_SAMPLE:
                continue
            # Score: profit_factor * win_rate/100 * log(sample) / (1 + drawdown)
            import math
            score = (
                m["profit_factor"] *
                (m["win_rate"] / 100.0) *
                math.log1p(m["resolved"]) /
                (1.0 + m["max_drawdown"])
            )
            results.append(CombinationStats(
                criteria      = combo,
                criteria_key  = key,
                sample_size   = m["resolved"],
                wins          = m["wins"],
                losses        = m["losses"],
                win_rate      = m["win_rate"],
                profit_factor = m["profit_factor"],
                expectancy    = m["expectancy"],
                sharpe        = m["sharpe"],
                max_drawdown  = m["max_drawdown"],
                score         = round(score, 4),
            ))

        results.sort(key=lambda x: x.score, reverse=True)
        top = results[:top_n]

        return CombinationReport(
            top_all  = top,
            top_buy  = top[:top_n],   # filtro de side requer dados extras
            top_sell = top[:top_n],
            analyzed = analyzed,
            valid    = valid,
        )

    async def _load_resolved_signals(self, symbol, lookback_days):
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        try:
            async with AsyncSessionLocal() as db:
                q = select(SignalHistory).where(
                    SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                    SignalHistory.emitted_at >= cutoff,
                    SignalHistory.pnl_pct.isnot(None),
                    SignalHistory.criteria_met.isnot(None),
                )
                if symbol:
                    q = q.where(SignalHistory.symbol == symbol)
                result = await db.execute(q.order_by(SignalHistory.emitted_at))
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[combination] load: %s", e)
            return []


combination_analyzer = CombinationAnalyzer()
