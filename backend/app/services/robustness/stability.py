"""
Fase 10 — Strategy Stability Analyzer
Avalia a estabilidade da estratégia por dimensão (símbolo, regime, timeframe, período).
Marca como UNSTABLE quando desvio do WR excede limites configurados.
Determinístico, auditável, sem IA.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

MIN_SAMPLE_PER_CELL = 5      # mínimo de trades para analisar uma célula
UNSTABLE_WR_DEVIATION = 15.0  # desvio máximo aceitável de WR vs baseline (pp)
UNSTABLE_PF_DEVIATION = 0.5   # desvio máximo aceitável de PF vs baseline
LOOKBACK_DAYS = 90


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class DimensionCell:
    """Resultado de uma dimensão/valor específico."""
    dimension_type:  str            # symbol | regime | timeframe | period
    dimension_value: str
    n_trades:        int            = 0
    win_rate:        float          = 0.0
    profit_factor:   float          = 0.0
    expectancy:      float          = 0.0
    baseline_wr:     float          = 0.0
    baseline_pf:     float          = 0.0
    wr_vs_baseline:  float          = 0.0    # delta pp
    pf_vs_baseline:  float          = 0.0    # delta abs
    stability_score: float          = 0.0    # 0-100
    is_unstable:     bool           = False
    unstable_reason: Optional[str]  = None


@dataclass
class StabilityReport:
    """Relatório de estabilidade por dimensão."""
    symbol:          Optional[str]      = None
    pattern_key:     Optional[str]      = None
    n_total_trades:  int                = 0
    baseline_wr:     float              = 0.0
    baseline_pf:     float              = 0.0
    by_symbol:       list[DimensionCell] = field(default_factory=list)
    by_regime:       list[DimensionCell] = field(default_factory=list)
    by_timeframe:    list[DimensionCell] = field(default_factory=list)
    by_period:       list[DimensionCell] = field(default_factory=list)
    overall_stability_score: float      = 0.0
    n_unstable_cells:        int        = 0
    computed_at:             datetime   = field(default_factory=datetime.utcnow)


# ── Stability Analyzer ────────────────────────────────────────────────────────

class StrategyStabilityAnalyzer:
    """
    Analisa estabilidade da estratégia por dimensão.
    Sem IA — análise estatística pura e determinística.
    """

    async def analyze(
        self,
        symbol:       Optional[str] = None,
        pattern_key:  Optional[str] = None,
        lookback_days: int          = LOOKBACK_DAYS,
        persist:      bool          = True,
    ) -> StabilityReport:
        """Executa análise completa de estabilidade."""
        rows = await self._load(symbol, pattern_key, lookback_days)
        n = len(rows)

        if n < MIN_SAMPLE_PER_CELL:
            return StabilityReport(symbol=symbol, pattern_key=pattern_key, n_total_trades=n)

        # Baseline: métricas globais de todos os trades
        baseline_wr, baseline_pf = _global_metrics(rows)

        # Análise por dimensão
        by_symbol    = _analyze_dimension(rows, "symbol",    baseline_wr, baseline_pf)
        by_regime    = _analyze_dimension(rows, "regime",    baseline_wr, baseline_pf)
        by_timeframe = _analyze_dimension(rows, "timeframe", baseline_wr, baseline_pf)
        by_period    = _analyze_period(rows, baseline_wr, baseline_pf)

        all_cells = by_symbol + by_regime + by_timeframe + by_period
        n_unstable = sum(1 for c in all_cells if c.is_unstable)

        # Score de estabilidade global: penaliza proporcionalmente às células instáveis
        if all_cells:
            avg_cell_score = sum(c.stability_score for c in all_cells) / len(all_cells)
        else:
            avg_cell_score = 100.0

        report = StabilityReport(
            symbol          = symbol,
            pattern_key     = pattern_key,
            n_total_trades  = n,
            baseline_wr     = round(baseline_wr, 2),
            baseline_pf     = round(baseline_pf, 3),
            by_symbol       = by_symbol,
            by_regime       = by_regime,
            by_timeframe    = by_timeframe,
            by_period       = by_period,
            overall_stability_score = round(avg_cell_score, 1),
            n_unstable_cells        = n_unstable,
            computed_at             = datetime.utcnow(),
        )

        if persist:
            await self._persist(report)

        return report

    async def _load(
        self,
        symbol:       Optional[str],
        pattern_key:  Optional[str],
        lookback_days: int,
    ) -> list:
        """Carrega trades resolvidos para análise."""
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
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
                rows = list(result.scalars().all())

            if pattern_key:
                pattern_criteria = set(pattern_key.split("|"))
                filtered = []
                for r in rows:
                    if not r.criteria_met:
                        continue
                    try:
                        clist = set(json.loads(r.criteria_met))
                        if pattern_criteria.issubset(clist):
                            filtered.append(r)
                    except Exception:
                        pass
                return filtered

            return rows
        except Exception as exc:
            logger.error("[stability] _load: %s", exc)
            return []

    async def _persist(self, report: StabilityReport) -> None:
        """Persiste células de estabilidade no banco."""
        try:
            from app.models.robustness import StrategyStability
            async with AsyncSessionLocal() as db:
                all_cells = (
                    report.by_symbol + report.by_regime
                    + report.by_timeframe + report.by_period
                )
                for cell in all_cells:
                    obj = StrategyStability(
                        pattern_key      = report.pattern_key,
                        dimension_type   = cell.dimension_type,
                        dimension_value  = cell.dimension_value,
                        n_trades         = cell.n_trades,
                        win_rate         = cell.win_rate,
                        profit_factor    = cell.profit_factor,
                        expectancy       = cell.expectancy,
                        baseline_wr      = cell.baseline_wr,
                        baseline_pf      = cell.baseline_pf,
                        wr_vs_baseline   = cell.wr_vs_baseline,
                        stability_score  = cell.stability_score,
                        is_unstable      = cell.is_unstable,
                        unstable_reason  = cell.unstable_reason,
                        computed_at      = report.computed_at,
                    )
                    db.add(obj)
                await db.commit()
        except Exception as exc:
            logger.error("[stability] _persist: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _global_metrics(rows: list) -> tuple[float, float]:
    """Calcula WR e PF globais (baseline)."""
    wins      = [r for r in rows if r.outcome == SignalOutcome.WIN]
    losses    = [r for r in rows if r.outcome == SignalOutcome.LOSS]
    wr        = len(wins) / len(rows) * 100.0 if rows else 0.0
    avg_win   = sum(r.pnl_pct for r in wins)   / len(wins)   if wins   else 0.0
    avg_loss  = abs(sum(r.pnl_pct for r in losses) / len(losses)) if losses else 1.0
    pf        = avg_win / avg_loss if avg_loss > 0 else 0.0
    return wr, pf


def _cell_metrics(subset: list) -> tuple[int, float, float, float]:
    """Retorna (n, win_rate, profit_factor, expectancy) para um subconjunto."""
    n = len(subset)
    if n == 0:
        return 0, 0.0, 0.0, 0.0
    wins   = [r for r in subset if r.outcome == SignalOutcome.WIN]
    losses = [r for r in subset if r.outcome == SignalOutcome.LOSS]
    wr     = len(wins) / n * 100.0
    avg_win  = sum(r.pnl_pct for r in wins)   / len(wins)   if wins   else 0.0
    avg_loss = abs(sum(r.pnl_pct for r in losses) / len(losses)) if losses else 1.0
    pf       = avg_win / avg_loss if avg_loss > 0 else 0.0
    exp      = sum(r.pnl_pct for r in subset) / n
    return n, round(wr, 2), round(pf, 3), round(exp, 3)


def _stability_score(wr_dev: float, pf_dev: float) -> tuple[float, bool, Optional[str]]:
    """
    Calcula stability_score (0-100) e sinaliza UNSTABLE se desvio excede limites.
    Penalidade linear: -2 pts por pp de desvio de WR, -5 pts por unidade de PF.
    """
    wr_penalty = min(abs(wr_dev) * 2.0, 50.0)
    pf_penalty = min(abs(pf_dev) * 5.0, 50.0)
    score = max(0.0, 100.0 - wr_penalty - pf_penalty)

    is_unstable = False
    reason = None
    reasons = []
    if abs(wr_dev) > UNSTABLE_WR_DEVIATION:
        is_unstable = True
        reasons.append(f"WR_DESVIO={wr_dev:+.1f}pp")
    if abs(pf_dev) > UNSTABLE_PF_DEVIATION:
        is_unstable = True
        reasons.append(f"PF_DESVIO={pf_dev:+.2f}")
    if reasons:
        reason = "; ".join(reasons)

    return round(score, 1), is_unstable, reason


def _analyze_dimension(
    rows: list,
    dimension: str,   # "symbol" | "regime" | "timeframe"
    baseline_wr: float,
    baseline_pf: float,
) -> list[DimensionCell]:
    """Agrupa por dimensão e analisa cada célula."""
    groups: dict[str, list] = {}
    for r in rows:
        key = None
        if dimension == "symbol":
            key = getattr(r, "symbol", None) or "N/A"
        elif dimension == "regime":
            key = getattr(r, "regime", None) or "UNKNOWN"
        elif dimension == "timeframe":
            key = getattr(r, "timeframe", None) or "1h"
        if key:
            groups.setdefault(key, []).append(r)

    cells = []
    for val, subset in sorted(groups.items()):
        n, wr, pf, exp = _cell_metrics(subset)
        if n < MIN_SAMPLE_PER_CELL:
            continue
        wr_delta = wr - baseline_wr
        pf_delta = pf - baseline_pf
        score, unstable, reason = _stability_score(wr_delta, pf_delta)
        cells.append(DimensionCell(
            dimension_type  = dimension,
            dimension_value = val,
            n_trades        = n,
            win_rate        = wr,
            profit_factor   = pf,
            expectancy      = exp,
            baseline_wr     = round(baseline_wr, 2),
            baseline_pf     = round(baseline_pf, 3),
            wr_vs_baseline  = round(wr_delta, 2),
            pf_vs_baseline  = round(pf_delta, 3),
            stability_score = score,
            is_unstable     = unstable,
            unstable_reason = reason,
        ))
    return cells


def _analyze_period(
    rows: list,
    baseline_wr: float,
    baseline_pf: float,
    n_periods: int = 3,
) -> list[DimensionCell]:
    """Divide em N períodos cronológicos e analisa cada um."""
    if not rows:
        return []
    rows_sorted = sorted(rows, key=lambda r: r.emitted_at)
    chunk_size  = max(1, len(rows_sorted) // n_periods)
    cells       = []
    for i in range(n_periods):
        subset = rows_sorted[i * chunk_size: (i + 1) * chunk_size]
        if not subset:
            continue
        label = f"P{i+1}({subset[0].emitted_at.strftime('%d/%m')}–{subset[-1].emitted_at.strftime('%d/%m')})"
        n, wr, pf, exp = _cell_metrics(subset)
        if n < MIN_SAMPLE_PER_CELL:
            continue
        wr_delta = wr - baseline_wr
        pf_delta = pf - baseline_pf
        score, unstable, reason = _stability_score(wr_delta, pf_delta)
        cells.append(DimensionCell(
            dimension_type  = "period",
            dimension_value = label,
            n_trades        = n,
            win_rate        = wr,
            profit_factor   = pf,
            expectancy      = exp,
            baseline_wr     = round(baseline_wr, 2),
            baseline_pf     = round(baseline_pf, 3),
            wr_vs_baseline  = round(wr_delta, 2),
            pf_vs_baseline  = round(pf_delta, 3),
            stability_score = score,
            is_unstable     = unstable,
            unstable_reason = reason,
        ))
    return cells


# ── Singleton ─────────────────────────────────────────────────────────────────

strategy_stability_analyzer = StrategyStabilityAnalyzer()
