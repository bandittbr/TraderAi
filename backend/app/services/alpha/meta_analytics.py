"""
Fase 9 — Meta-Analytics Engine
Calcula as melhores configurações globais para o sistema:
  - Melhor ativo
  - Melhor timeframe
  - Melhor regime
  - Melhor contexto
  - Melhor combinação SMC
  - Melhor combinação técnica
Tudo determinístico — sem IA.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome
from app.services.optimizer.criterion_performance import _compute_metrics

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 90
MIN_SAMPLE    = 5


@dataclass
class DimensionStats:
    """Métricas para uma dimensão específica (ativo, regime, etc.)"""
    dimension:     str           # ex: "BTCUSDT", "BULL", "1h"
    dimension_type: str          # ex: "symbol", "regime", "timeframe"
    resolved:      int  = 0
    wins:          int  = 0
    win_rate:      float = 0.0
    profit_factor: float = 0.0
    expectancy:    float = 0.0
    sharpe:        float = 0.0
    score:         float = 0.0   # score composto para ranking


@dataclass
class MetaAnalyticsReport:
    """Relatório completo de meta-analytics."""
    computed_at:       datetime                = field(default_factory=datetime.utcnow)
    # Rankings por dimensão
    by_symbol:         list[DimensionStats]    = field(default_factory=list)
    by_timeframe:      list[DimensionStats]    = field(default_factory=list)
    by_regime:         list[DimensionStats]    = field(default_factory=list)
    by_context:        list[DimensionStats]    = field(default_factory=list)   # por fear_greed_label
    by_smc_combo:      list[DimensionStats]    = field(default_factory=list)   # sweep+fvg combos
    by_technical:      list[DimensionStats]    = field(default_factory=list)   # ema+rsi combos
    # Melhores (top 1 de cada)
    best_symbol:       Optional[str]           = None
    best_timeframe:    Optional[str]           = None
    best_regime:       Optional[str]           = None
    best_context:      Optional[str]           = None
    best_smc_combo:    Optional[str]           = None
    best_technical:    Optional[str]           = None
    total_resolved:    int                     = 0
    baseline_wr:       float                   = 0.0
    baseline_pf:       float                   = 0.0


class MetaAnalyticsEngine:
    """Analisa o histórico global para encontrar as melhores configurações."""

    async def compute(self, lookback_days: int = LOOKBACK_DAYS) -> MetaAnalyticsReport:
        rows = await self._load_resolved(lookback_days)
        if not rows:
            return MetaAnalyticsReport()

        baseline = _compute_metrics(rows)
        report   = MetaAnalyticsReport(
            total_resolved = baseline["resolved"],
            baseline_wr    = baseline["win_rate"],
            baseline_pf    = baseline["profit_factor"],
        )

        # ── Por ativo ─────────────────────────────────────────────────────
        report.by_symbol    = self._group_by(rows, lambda r: r.symbol, "symbol")
        # ── Por timeframe ─────────────────────────────────────────────────
        report.by_timeframe = self._group_by(rows, lambda r: r.timeframe, "timeframe")
        # ── Por regime ────────────────────────────────────────────────────
        report.by_regime    = self._group_by(rows, lambda r: str(r.regime.value) if r.regime else "UNKNOWN", "regime")
        # ── Por contexto (fear & greed label) ─────────────────────────────
        report.by_context   = self._group_by(rows, lambda r: r.fear_greed_label or "UNKNOWN", "context")
        # ── Por combinação SMC ────────────────────────────────────────────
        report.by_smc_combo = self._group_smc(rows)
        # ── Por combinação técnica ────────────────────────────────────────
        report.by_technical = self._group_technical(rows)

        # ── Melhores ──────────────────────────────────────────────────────
        def best_of(lst: list[DimensionStats]) -> Optional[str]:
            valid = [d for d in lst if d.resolved >= MIN_SAMPLE]
            return valid[0].dimension if valid else None

        report.best_symbol    = best_of(report.by_symbol)
        report.best_timeframe = best_of(report.by_timeframe)
        report.best_regime    = best_of(report.by_regime)
        report.best_context   = best_of(report.by_context)
        report.best_smc_combo = best_of(report.by_smc_combo)
        report.best_technical = best_of(report.by_technical)

        return report

    def _group_by(
        self, rows: list, key_fn, dim_type: str
    ) -> list[DimensionStats]:
        """Agrupa sinais por uma dimensão e calcula métricas."""
        groups: dict[str, list] = {}
        for r in rows:
            k = key_fn(r) or "UNKNOWN"
            groups.setdefault(k, []).append(r)

        result = []
        for dim, group_rows in groups.items():
            m = _compute_metrics(group_rows)
            if m["resolved"] < 1:
                continue
            score = m["win_rate"] * 0.5 + min(m["profit_factor"] / 3.0, 1.0) * 50.0
            result.append(DimensionStats(
                dimension      = dim,
                dimension_type = dim_type,
                resolved       = m["resolved"],
                wins           = m["wins"],
                win_rate       = m["win_rate"],
                profit_factor  = m["profit_factor"],
                expectancy     = m["expectancy"],
                sharpe         = m["sharpe"],
                score          = round(score, 2),
            ))

        result.sort(key=lambda d: d.score, reverse=True)
        return result

    def _group_smc(self, rows: list) -> list[DimensionStats]:
        """Agrupa por combinação de flags SMC: had_sweep, had_fvg, had_hvn."""
        groups: dict[str, list] = {}
        for r in rows:
            parts = []
            if r.had_sweep: parts.append("sweep")
            if r.had_fvg:   parts.append("fvg")
            if r.had_hvn:   parts.append("hvn")
            key = "+".join(parts) if parts else "none"
            groups.setdefault(key, []).append(r)

        result = []
        for dim, group_rows in groups.items():
            m = _compute_metrics(group_rows)
            if m["resolved"] < MIN_SAMPLE:
                continue
            score = m["win_rate"] * 0.5 + min(m["profit_factor"] / 3.0, 1.0) * 50.0
            result.append(DimensionStats(
                dimension      = dim,
                dimension_type = "smc_combo",
                resolved       = m["resolved"],
                wins           = m["wins"],
                win_rate       = m["win_rate"],
                profit_factor  = m["profit_factor"],
                expectancy     = m["expectancy"],
                sharpe         = m["sharpe"],
                score          = round(score, 2),
            ))

        result.sort(key=lambda d: d.score, reverse=True)
        return result

    def _group_technical(self, rows: list) -> list[DimensionStats]:
        """
        Agrupa por combinação de critérios técnicos principais:
        ema, rsi, macd (presença detectada em criteria_met).
        """
        TECH_CRITERIA = {
            "ema":      {"ema_bull", "ema_bear", "ema_macro_bull", "ema_macro_bear", "ema_price_above", "ema_price_below"},
            "rsi":      {"rsi_ok", "rsi_high"},
            "macd":     {"macd_positive", "macd_negative", "macd_cross", "macd_cross_down"},
            "bos":      {"bos_bullish", "bos_bearish"},
            "sr_zone":  {"price_near_support", "price_near_resistance"},
        }

        groups: dict[str, list] = {}
        for r in rows:
            if not r.criteria_met:
                groups.setdefault("none", []).append(r)
                continue
            try:
                clist = set(json.loads(r.criteria_met))
            except Exception:
                groups.setdefault("none", []).append(r)
                continue

            active = []
            for tech, tech_crits in TECH_CRITERIA.items():
                if clist & tech_crits:
                    active.append(tech)
            key = "+".join(sorted(active)) if active else "none"
            groups.setdefault(key, []).append(r)

        result = []
        for dim, group_rows in groups.items():
            m = _compute_metrics(group_rows)
            if m["resolved"] < MIN_SAMPLE:
                continue
            score = m["win_rate"] * 0.5 + min(m["profit_factor"] / 3.0, 1.0) * 50.0
            result.append(DimensionStats(
                dimension      = dim,
                dimension_type = "technical",
                resolved       = m["resolved"],
                wins           = m["wins"],
                win_rate       = m["win_rate"],
                profit_factor  = m["profit_factor"],
                expectancy     = m["expectancy"],
                sharpe         = m["sharpe"],
                score          = round(score, 2),
            ))

        result.sort(key=lambda d: d.score, reverse=True)
        return result

    async def _load_resolved(self, lookback_days: int) -> list:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(SignalHistory)
                    .where(
                        SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                        SignalHistory.emitted_at >= cutoff,
                        SignalHistory.pnl_pct.isnot(None),
                    )
                    .order_by(SignalHistory.emitted_at)
                )
                result = await db.execute(q)
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[alpha] meta _load_resolved: %s", e)
            return []


# ── Singleton ─────────────────────────────────────────────────────────────────

meta_analytics_engine = MetaAnalyticsEngine()
