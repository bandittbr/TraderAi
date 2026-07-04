"""
Strategy Analytics — Phase 6

Analisa o histórico de sinais para identificar:
  1. Correlação de indicadores com vitórias (qual critério prevê wins?)
  2. Performance por ativo (qual símbolo tem maior WR?)
  3. Performance por regime (qual regime é mais favorável?)
  4. Melhor combinação de critérios (top-N combos por WR)
  5. Snapshot geral de métricas por (symbol, regime, period)

Todas as análises são DETERMINÍSTICAS (baseadas em dados históricos reais do DB).
Nenhuma IA generativa.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from itertools import combinations
from typing import Any, Optional

from sqlalchemy import select, and_, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.analytics import (
    SignalHistory, SignalOutcome, MarketRegimeType,
    StrategyPerformanceSnapshot,
)
from app.services.signal_analytics.metrics_engine import compute_metrics

logger = logging.getLogger(__name__)

# Critérios que ficam registrados em criteria_met (JSON)
KNOWN_CRITERIA = [
    "rsi_ok",
    "ema_bull",
    "ema_micro_bull",
    "ema_price_above",
    "macd_positive",
    "macd_cross",
    "ema_bear",
    "ema_micro_bear",
    "ema_price_below",
    "macd_negative",
    "macd_cross_bear",
]

MAX_COMBO_SIZE = 3   # Máximo de critérios no combo analisado


# ─────────────────────────────────────────────
# Estruturas de resultado
# ─────────────────────────────────────────────

class AnalyticsResult:
    __slots__ = (
        "symbol", "regime", "period_days",
        "total_signals", "resolved_signals",
        "buy_signals", "sell_signals",
        "wins", "losses",
        "win_rate", "profit_factor", "expectancy",
        "sharpe_ratio", "calmar_ratio", "max_drawdown",
        "avg_pnl_pct", "avg_win_pct", "avg_loss_pct",
        "avg_duration_min",
        # LONG vs SHORT
        "long_trades", "short_trades",
        "win_rate_long", "win_rate_short",
        "pf_long", "pf_short",
        "indicator_win_rates",     # dict: criterion → win_rate%
        "best_combination",        # list[str] de até MAX_COMBO_SIZE critérios
        "per_asset",               # dict: symbol → {win_rate, total}
        "per_regime",              # dict: regime → {win_rate, total}
        "computed_at",
    )

    def __init__(self, **kw: Any):
        for k, v in kw.items():
            setattr(self, k, v)
        self.computed_at = datetime.utcnow()


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_pnls(
    records: list[SignalHistory],
) -> tuple[list[float], list[int], list[str]]:
    """Extrai listas de pnl_pct, durations_min e sides dos registros resolvidos."""
    pnls  = []
    durs  = []
    sides = []
    for r in records:
        if r.pnl_pct is not None:
            pnls.append(float(r.pnl_pct))
            durs.append(int(r.trade_duration_min) if r.trade_duration_min is not None else 0)
            sides.append(getattr(r, "trade_side", None) or "LONG")
    return pnls, [d for d in durs if d], sides


def _criterion_win_rate(
    records: list[SignalHistory],
    criterion: str,
) -> Optional[float]:
    """
    Calcula o win rate dos trades em que `criterion` estava nos critérios atendidos.
    Retorna None se não houver dados suficientes (< 3 trades com o critério).
    """
    matching = []
    for r in records:
        if not r.criteria_met:
            continue
        try:
            criteria = json.loads(r.criteria_met)
        except (json.JSONDecodeError, TypeError):
            continue
        if criterion in criteria and r.pnl_pct is not None:
            matching.append(r.pnl_pct)

    if len(matching) < 3:
        return None
    wins = sum(1 for p in matching if p > 0)
    return round((wins / len(matching)) * 100.0, 2)


def _combo_win_rate(
    records: list[SignalHistory],
    combo: tuple[str, ...],
) -> tuple[float, int]:
    """
    Win rate da interseção de critérios do combo.
    Retorna (win_rate%, sample_size).
    """
    matching = []
    for r in records:
        if not r.criteria_met:
            continue
        try:
            criteria_set = set(json.loads(r.criteria_met))
        except (json.JSONDecodeError, TypeError):
            continue
        if set(combo).issubset(criteria_set) and r.pnl_pct is not None:
            matching.append(r.pnl_pct)

    if len(matching) < 3:
        return 0.0, 0
    wins = sum(1 for p in matching if p > 0)
    wr   = (wins / len(matching)) * 100.0
    return round(wr, 2), len(matching)


def _group_by_symbol(
    records: list[SignalHistory],
) -> dict[str, list[float]]:
    """Agrupa pnl_pct por símbolo."""
    groups: dict[str, list[float]] = {}
    for r in records:
        if r.pnl_pct is None:
            continue
        groups.setdefault(r.symbol, []).append(float(r.pnl_pct))
    return groups


def _group_by_regime(
    records: list[SignalHistory],
) -> dict[str, list[float]]:
    """Agrupa pnl_pct por regime."""
    groups: dict[str, list[float]] = {}
    for r in records:
        if r.pnl_pct is None:
            continue
        reg = r.regime.value if r.regime else "UNKNOWN"
        groups.setdefault(reg, []).append(float(r.pnl_pct))
    return groups


# ─────────────────────────────────────────────
# Strategy Analytics Service
# ─────────────────────────────────────────────

class StrategyAnalytics:

    async def _fetch_resolved(
        self,
        db: AsyncSession,
        *,
        symbol: Optional[str],
        regime: Optional[MarketRegimeType],
        period_days: int,
        signal_direction: Optional[str] = None,
    ) -> list[SignalHistory]:
        """Busca sinais WIN ou LOSS dentro do período/filtros."""
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        conditions = [
            SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
            SignalHistory.emitted_at >= cutoff,
        ]
        if symbol:
            conditions.append(SignalHistory.symbol == symbol)
        if regime:
            conditions.append(SignalHistory.regime == regime)
        if signal_direction:
            from app.models.analytics import SignalDirection
            sd = SignalDirection(signal_direction.upper())
            conditions.append(SignalHistory.signal == sd)

        result = await db.execute(
            select(SignalHistory).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def _fetch_all_by_period(
        self,
        db: AsyncSession,
        period_days: int,
    ) -> list[SignalHistory]:
        """Busca todos os sinais (incluindo OPEN/MISSED) do período."""
        cutoff = datetime.utcnow() - timedelta(days=period_days)
        result = await db.execute(
            select(SignalHistory).where(SignalHistory.emitted_at >= cutoff)
        )
        return list(result.scalars().all())

    async def analyze(
        self,
        symbol:      Optional[str]            = None,
        regime:      Optional[MarketRegimeType] = None,
        period_days: int                       = 30,
    ) -> AnalyticsResult:
        """
        Análise completa de performance para os filtros dados.
        Todas as computações são determinísticas sobre dados do DB.
        """
        try:
            async with AsyncSessionLocal() as db:
                resolved = await self._fetch_resolved(
                    db, symbol=symbol, regime=regime, period_days=period_days
                )
                all_records = await self._fetch_all_by_period(db, period_days)
        except Exception as exc:
            logger.error("strategy_analytics.analyze falhou: %s", exc)
            return AnalyticsResult(
                symbol=symbol, regime=regime, period_days=period_days,
                total_signals=0, resolved_signals=0,
                buy_signals=0, sell_signals=0,
                wins=0, losses=0,
                win_rate=0.0, profit_factor=0.0, expectancy=0.0,
                sharpe_ratio=0.0, calmar_ratio=0.0, max_drawdown=0.0,
                avg_pnl_pct=0.0, avg_win_pct=0.0, avg_loss_pct=0.0,
                avg_duration_min=0.0,
                long_trades=0, short_trades=0,
                win_rate_long=0.0, win_rate_short=0.0,
                pf_long=0.0, pf_short=0.0,
                indicator_win_rates={}, best_combination=[],
                per_asset={}, per_regime={},
            )

        pnls, durs, sides = _extract_pnls(resolved)
        metrics           = compute_metrics(pnls, durs, sides=sides)

        # ── Contagens gerais ─────────────────────────────────
        total_signals = len(all_records)
        from app.models.analytics import SignalDirection
        buy_count  = sum(1 for r in all_records if r.signal == SignalDirection.BUY)
        sell_count = sum(1 for r in all_records if r.signal == SignalDirection.SELL)

        # ── Correlação indicadores × vitórias ───────────────
        indicator_wr: dict[str, float] = {}
        for crit in KNOWN_CRITERIA:
            wr = _criterion_win_rate(resolved, crit)
            if wr is not None:
                indicator_wr[crit] = wr

        # ── Melhor combinação de critérios ──────────────────
        best_combo: list[str] = []
        best_combo_wr = 0.0
        available_criteria = [c for c in KNOWN_CRITERIA if c in indicator_wr]

        for size in range(2, min(MAX_COMBO_SIZE + 1, len(available_criteria) + 1)):
            for combo in combinations(available_criteria, size):
                wr_c, n = _combo_win_rate(resolved, combo)
                if n >= 3 and wr_c > best_combo_wr:
                    best_combo_wr = wr_c
                    best_combo = list(combo)

        # ── Por ativo ────────────────────────────────────────
        per_asset: dict[str, Any] = {}
        by_symbol = _group_by_symbol(resolved)
        for sym, sym_pnls in by_symbol.items():
            wins = sum(1 for p in sym_pnls if p > 0)
            per_asset[sym] = {
                "win_rate": round((wins / len(sym_pnls)) * 100, 2),
                "total":    len(sym_pnls),
                "avg_pnl":  round(sum(sym_pnls) / len(sym_pnls), 4),
            }

        # ── Por regime ───────────────────────────────────────
        per_regime: dict[str, Any] = {}
        by_regime = _group_by_regime(resolved)
        for reg_name, reg_pnls in by_regime.items():
            wins = sum(1 for p in reg_pnls if p > 0)
            per_regime[reg_name] = {
                "win_rate": round((wins / len(reg_pnls)) * 100, 2),
                "total":    len(reg_pnls),
                "avg_pnl":  round(sum(reg_pnls) / len(reg_pnls), 4),
            }

        return AnalyticsResult(
            symbol            = symbol,
            regime            = regime,
            period_days       = period_days,
            total_signals     = total_signals,
            resolved_signals  = len(resolved),
            buy_signals       = buy_count,
            sell_signals      = sell_count,
            wins              = metrics.wins,
            losses            = metrics.losses,
            win_rate          = metrics.win_rate,
            profit_factor     = metrics.profit_factor,
            expectancy        = metrics.expectancy,
            sharpe_ratio      = metrics.sharpe_ratio,
            calmar_ratio      = metrics.calmar_ratio,
            max_drawdown      = metrics.max_drawdown,
            avg_pnl_pct       = metrics.avg_pnl_pct,
            avg_win_pct       = metrics.avg_win_pct,
            avg_loss_pct      = metrics.avg_loss_pct,
            avg_duration_min  = metrics.avg_duration_min,
            long_trades       = metrics.long_trades,
            short_trades      = metrics.short_trades,
            win_rate_long     = metrics.win_rate_long,
            win_rate_short    = metrics.win_rate_short,
            pf_long           = metrics.pf_long,
            pf_short          = metrics.pf_short,
            indicator_win_rates = indicator_wr,
            best_combination  = best_combo,
            per_asset         = per_asset,
            per_regime        = per_regime,
        )

    async def save_snapshot(
        self,
        result: AnalyticsResult,
    ) -> None:
        """Persiste um AnalyticsResult como StrategyPerformanceSnapshot no DB."""
        try:
            async with AsyncSessionLocal() as db:
                snap = StrategyPerformanceSnapshot(
                    symbol            = result.symbol or "ALL",
                    regime            = result.regime,
                    period_days       = result.period_days,
                    total_signals     = result.total_signals,
                    buy_signals       = result.buy_signals,
                    sell_signals      = result.sell_signals,
                    resolved_signals  = result.resolved_signals,
                    wins              = result.wins,
                    losses            = result.losses,
                    win_rate          = result.win_rate,
                    profit_factor     = result.profit_factor,
                    expectancy        = result.expectancy,
                    sharpe_ratio      = result.sharpe_ratio,
                    calmar_ratio      = result.calmar_ratio,
                    max_drawdown      = result.max_drawdown,
                    avg_pnl_pct       = result.avg_pnl_pct,
                    avg_win_pct       = result.avg_win_pct,
                    avg_loss_pct      = result.avg_loss_pct,
                    avg_duration_min  = result.avg_duration_min,
                    indicator_win_rates = json.dumps(result.indicator_win_rates),
                    best_combination    = json.dumps(result.best_combination),
                    computed_at       = result.computed_at,
                )
                db.add(snap)
                await db.commit()
        except Exception as exc:
            logger.error("strategy_analytics.save_snapshot falhou: %s", exc)

    async def get_signal_history(
        self,
        symbol:      Optional[str] = None,
        period_days: int           = 7,
        limit:       int           = 100,
    ) -> list[SignalHistory]:
        """Retorna histórico recente de sinais para exibição no frontend."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=period_days)
            conditions = [SignalHistory.emitted_at >= cutoff]
            if symbol:
                conditions.append(SignalHistory.symbol == symbol)

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SignalHistory)
                    .where(and_(*conditions))
                    .order_by(SignalHistory.emitted_at.desc())
                    .limit(limit)
                )
                return list(result.scalars().all())
        except Exception as exc:
            logger.error("strategy_analytics.get_signal_history falhou: %s", exc)
            return []

    async def get_current_regime(self, symbol: str) -> Optional[Any]:
        """Retorna o regime mais recente para um símbolo."""
        try:
            from app.models.analytics import MarketRegime
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(MarketRegime)
                    .where(MarketRegime.symbol == symbol)
                    .order_by(MarketRegime.timestamp.desc())
                    .limit(1)
                )
                return result.scalar_one_or_none()
        except Exception as exc:
            logger.error("strategy_analytics.get_current_regime falhou: %s", exc)
            return None


# ─────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────

strategy_analytics = StrategyAnalytics()
