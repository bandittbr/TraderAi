"""
Fase 10 — Walk Forward Validator
Divide o histórico em 3 fases (train/validation/test) e calcula métricas em cada uma.
Detecta degradação de performance entre treino e teste (overfitting).
Tudo determinístico — sem IA.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome
from app.services.optimizer.criterion_performance import _compute_metrics, _compute_max_drawdown

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_TRAIN_DAYS = 60
DEFAULT_VAL_DAYS   = 30
DEFAULT_TEST_DAYS  = 30
MIN_SAMPLE         = 5   # mínimo de trades em cada fase para ser válido

# Limites de degradação aceitável
MAX_WR_DEGRADATION  = 10.0   # máximo de queda WR aceitável (pp)
MAX_PF_DEGRADATION  = 0.3    # máximo de queda PF aceitável
MAX_DD_INCREASE     = 5.0    # máximo de aumento DD aceitável (pp)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PhaseMetrics:
    """Métricas de uma fase (train/val/test)."""
    phase:         str     # "train" | "validation" | "test"
    n_trades:      int     = 0
    win_rate:      float   = 0.0
    profit_factor: float   = 0.0
    sharpe:        float   = 0.0
    expectancy:    float   = 0.0
    max_drawdown:  float   = 0.0
    avg_win_pct:   float   = 0.0
    avg_loss_pct:  float   = 0.0
    sufficient:    bool    = False


@dataclass
class WalkForwardReport:
    """Resultado completo da Walk Forward Validation."""
    symbol:         Optional[str]    = None
    pattern_key:    Optional[str]    = None
    train_days:     int              = DEFAULT_TRAIN_DAYS
    val_days:       int              = DEFAULT_VAL_DAYS
    test_days:      int              = DEFAULT_TEST_DAYS
    train:          Optional[PhaseMetrics] = None
    validation:     Optional[PhaseMetrics] = None
    test:           Optional[PhaseMetrics] = None
    wr_degradation: float            = 0.0   # test_wr - train_wr
    pf_degradation: float            = 0.0   # test_pf - train_pf
    dd_increase:    float            = 0.0   # test_dd - train_dd
    wf_score:       float            = 0.0   # 0-100
    is_robust:      bool             = False
    computed_at:    datetime         = field(default_factory=datetime.utcnow)


# ── Walk Forward Engine ───────────────────────────────────────────────────────

class WalkForwardValidator:
    """
    Valida robustez de padrões/estratégias dividindo o histórico em janelas.
    """

    async def validate(
        self,
        symbol:        Optional[str] = None,
        pattern_key:   Optional[str] = None,
        train_days:    int           = DEFAULT_TRAIN_DAYS,
        val_days:      int           = DEFAULT_VAL_DAYS,
        test_days:     int           = DEFAULT_TEST_DAYS,
        persist:       bool          = True,
    ) -> WalkForwardReport:
        """Executa walk forward validation completo."""
        total_days = train_days + val_days + test_days
        now        = datetime.utcnow()

        # Definir janelas temporais
        test_end   = now
        test_start = test_end - timedelta(days=test_days)
        val_end    = test_start
        val_start  = val_end - timedelta(days=val_days)
        train_end  = val_start
        train_start = train_end - timedelta(days=train_days)

        # Carregar sinais de cada fase
        train_rows = await self._load(symbol, pattern_key, train_start, train_end)
        val_rows   = await self._load(symbol, pattern_key, val_start,   val_end)
        test_rows  = await self._load(symbol, pattern_key, test_start,  test_end)

        train_m = self._metrics("train",      train_rows)
        val_m   = self._metrics("validation", val_rows)
        test_m  = self._metrics("test",       test_rows)

        # Degradação
        wr_deg = (test_m.win_rate - train_m.win_rate) if (train_m.sufficient and test_m.sufficient) else 0.0
        pf_deg = (test_m.profit_factor - train_m.profit_factor) if (train_m.sufficient and test_m.sufficient) else 0.0
        dd_inc = (test_m.max_drawdown - train_m.max_drawdown) if (train_m.sufficient and test_m.sufficient) else 0.0

        wf_score = _compute_wf_score(train_m, val_m, test_m, wr_deg, pf_deg, dd_inc)
        is_robust = (
            wf_score >= 50.0
            and wr_deg >= -MAX_WR_DEGRADATION
            and pf_deg >= -MAX_PF_DEGRADATION
            and dd_inc <= MAX_DD_INCREASE
        )

        report = WalkForwardReport(
            symbol         = symbol,
            pattern_key    = pattern_key,
            train_days     = train_days,
            val_days       = val_days,
            test_days      = test_days,
            train          = train_m,
            validation     = val_m,
            test           = test_m,
            wr_degradation = round(wr_deg, 3),
            pf_degradation = round(pf_deg, 3),
            dd_increase    = round(dd_inc, 3),
            wf_score       = round(wf_score, 2),
            is_robust      = is_robust,
            computed_at    = datetime.utcnow(),
        )

        if persist:
            await self._persist(report)

        return report

    def _metrics(self, phase: str, rows: list) -> PhaseMetrics:
        """Calcula métricas de uma fase."""
        m = _compute_metrics(rows)
        return PhaseMetrics(
            phase         = phase,
            n_trades      = m["resolved"],
            win_rate      = m["win_rate"],
            profit_factor = m["profit_factor"],
            sharpe        = m["sharpe"],
            expectancy    = m["expectancy"],
            max_drawdown  = m["max_drawdown"],
            avg_win_pct   = m["avg_win_pct"],
            avg_loss_pct  = m["avg_loss_pct"],
            sufficient    = m["resolved"] >= MIN_SAMPLE,
        )

    async def _load(
        self,
        symbol:      Optional[str],
        pattern_key: Optional[str],
        start:       datetime,
        end:         datetime,
    ) -> list:
        """Carrega sinais resolvidos de um período."""
        try:
            async with AsyncSessionLocal() as db:
                q = (
                    select(SignalHistory)
                    .where(
                        SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                        SignalHistory.pnl_pct.isnot(None),
                        SignalHistory.emitted_at >= start,
                        SignalHistory.emitted_at < end,
                    )
                    .order_by(SignalHistory.emitted_at)
                )
                if symbol:
                    q = q.where(SignalHistory.symbol == symbol)
                result = await db.execute(q)
                rows = list(result.scalars().all())

                # Filtrar por pattern_key (criteria_met) se especificado
                if pattern_key:
                    import json
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
        except Exception as e:
            logger.error("[wf] _load: %s", e)
            return []

    async def _persist(self, report: WalkForwardReport) -> None:
        """Persiste resultado no banco."""
        try:
            from app.models.robustness import WalkForwardResult
            async with AsyncSessionLocal() as db:
                obj = WalkForwardResult(
                    symbol         = report.symbol,
                    pattern_key    = report.pattern_key,
                    train_days     = report.train_days,
                    val_days       = report.val_days,
                    test_days      = report.test_days,
                    # Train
                    train_n        = report.train.n_trades if report.train else None,
                    train_wr       = report.train.win_rate if report.train else None,
                    train_pf       = report.train.profit_factor if report.train else None,
                    train_sharpe   = report.train.sharpe if report.train else None,
                    train_exp      = report.train.expectancy if report.train else None,
                    train_dd       = report.train.max_drawdown if report.train else None,
                    # Validation
                    val_n          = report.validation.n_trades if report.validation else None,
                    val_wr         = report.validation.win_rate if report.validation else None,
                    val_pf         = report.validation.profit_factor if report.validation else None,
                    val_sharpe     = report.validation.sharpe if report.validation else None,
                    val_exp        = report.validation.expectancy if report.validation else None,
                    val_dd         = report.validation.max_drawdown if report.validation else None,
                    # Test
                    test_n         = report.test.n_trades if report.test else None,
                    test_wr        = report.test.win_rate if report.test else None,
                    test_pf        = report.test.profit_factor if report.test else None,
                    test_sharpe    = report.test.sharpe if report.test else None,
                    test_exp       = report.test.expectancy if report.test else None,
                    test_dd        = report.test.max_drawdown if report.test else None,
                    # Degradation
                    wr_degradation = report.wr_degradation,
                    pf_degradation = report.pf_degradation,
                    dd_increase    = report.dd_increase,
                    wf_score       = report.wf_score,
                    is_robust      = report.is_robust,
                    computed_at    = report.computed_at,
                )
                db.add(obj)
                await db.commit()
        except Exception as exc:
            logger.error("[wf] _persist: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_wf_score(
    train: PhaseMetrics,
    val:   PhaseMetrics,
    test:  PhaseMetrics,
    wr_deg: float,
    pf_deg: float,
    dd_inc: float,
) -> float:
    """
    Calcula Robustness Score Walk Forward (0-100).
    Base: 50 pontos se todas as fases têm dados suficientes.
    Bônus: consistência entre fases.
    Penalidade: degradação excessiva.
    """
    if not (train.sufficient and test.sufficient):
        return 20.0 if (train.sufficient or test.sufficient) else 0.0

    score = 50.0

    # Bônus por consistência WR (max +20)
    if wr_deg >= 0:
        score += 20.0
    elif wr_deg >= -5:
        score += 15.0
    elif wr_deg >= -10:
        score += 5.0
    else:
        score -= 10.0

    # Bônus por consistência PF (max +15)
    if pf_deg >= 0:
        score += 15.0
    elif pf_deg >= -0.2:
        score += 8.0
    elif pf_deg >= -0.5:
        score += 2.0
    else:
        score -= 10.0

    # Bônus por drawdown controlado (max +15)
    if dd_inc <= 0:
        score += 15.0
    elif dd_inc <= 3:
        score += 8.0
    elif dd_inc <= 8:
        score += 2.0
    else:
        score -= 10.0

    # Bônus por validation consistente com train (max +10)
    if val.sufficient:
        val_wr_diff = abs(val.win_rate - train.win_rate)
        if val_wr_diff <= 5:
            score += 10.0
        elif val_wr_diff <= 10:
            score += 5.0

    return max(0.0, min(100.0, score))


# ── Singleton ─────────────────────────────────────────────────────────────────

walk_forward_validator = WalkForwardValidator()
