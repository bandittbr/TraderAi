"""
Fase 10 — Monte Carlo Simulation Engine
Embaralha N vezes a sequência de trades históricos para estimar:
  - Distribuição de drawdowns (mediana, p95, p99)
  - Risco de ruína
  - Distribuição de retornos finais
  - Win rate esperado com intervalo de confiança
Determinístico via seed fixo para reprodutibilidade.
"""
from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

DEFAULT_N_SIM       = 5000    # número de simulações
DEFAULT_RUIN_THR    = 20.0    # drawdown % = ruína
RANDOM_SEED         = 42      # seed fixo para reprodutibilidade
LOOKBACK_DAYS       = 90


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class MonteCarloReport:
    """Resultado completo da simulação Monte Carlo."""
    symbol:          Optional[str]  = None
    pattern_key:     Optional[str]  = None
    n_simulations:   int            = DEFAULT_N_SIM
    n_trades:        int            = 0
    # Drawdown distribution
    dd_median:       float          = 0.0
    dd_p95:          float          = 0.0
    dd_p99:          float          = 0.0
    dd_max_observed: float          = 0.0
    # Return distribution
    ret_median:      float          = 0.0
    ret_p5:          float          = 0.0    # pior 5%
    ret_p95:         float          = 0.0    # melhor 5%
    # Risco de ruína
    ruin_threshold:  float          = DEFAULT_RUIN_THR
    ruin_probability: float         = 0.0    # 0-100
    # Win rate distribution
    expected_wr:     float          = 0.0
    wr_std:          float          = 0.0
    # Histograma de drawdowns (para gráfico)
    dd_histogram:    dict           = field(default_factory=dict)
    computed_at:     datetime       = field(default_factory=datetime.utcnow)


# ── Monte Carlo Engine ────────────────────────────────────────────────────────

class MonteCarloEngine:
    """
    Simula distribuições de risco via bootstrapping dos trades históricos.
    Sem IA — puro método estatístico determinístico.
    """

    async def simulate(
        self,
        symbol:         Optional[str]  = None,
        pattern_key:    Optional[str]  = None,
        n_simulations:  int            = DEFAULT_N_SIM,
        ruin_threshold: float          = DEFAULT_RUIN_THR,
        lookback_days:  int            = LOOKBACK_DAYS,
        persist:        bool           = True,
    ) -> MonteCarloReport:
        """Executa N simulações e retorna distribuição de resultados."""
        pnls = await self._load_pnls(symbol, pattern_key, lookback_days)
        n    = len(pnls)

        if n < 5:
            logger.info("[mc] trades insuficientes para Monte Carlo (n=%d)", n)
            return MonteCarloReport(
                symbol=symbol, pattern_key=pattern_key,
                n_simulations=n_simulations, n_trades=n,
            )

        rng = random.Random(RANDOM_SEED)

        sim_drawdowns:  list[float] = []
        sim_returns:    list[float] = []
        sim_wrs:        list[float] = []
        ruin_count:     int         = 0

        for _ in range(n_simulations):
            # Embaralha a sequência de trades
            shuffled = rng.sample(pnls, len(pnls))

            # Calcular equity curve e métricas
            equity    = 0.0
            peak      = 0.0
            max_dd    = 0.0
            wins      = 0
            hit_ruin  = False

            for pnl in shuffled:
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = peak - equity
                if dd > max_dd:
                    max_dd = dd
                if dd >= ruin_threshold:
                    hit_ruin = True
                if pnl > 0:
                    wins += 1

            sim_drawdowns.append(max_dd)
            sim_returns.append(equity)
            sim_wrs.append(wins / len(shuffled) * 100.0)
            if hit_ruin:
                ruin_count += 1

        # Calcular estatísticas
        sim_drawdowns.sort()
        sim_returns.sort()
        sim_wrs.sort()

        n_sim = len(sim_drawdowns)
        p50   = sim_drawdowns[int(n_sim * 0.50)]
        p95   = sim_drawdowns[int(n_sim * 0.95)]
        p99   = sim_drawdowns[min(int(n_sim * 0.99), n_sim - 1)]
        max_obs = sim_drawdowns[-1]

        ret_med  = sim_returns[int(n_sim * 0.50)]
        ret_p5   = sim_returns[int(n_sim * 0.05)]
        ret_p95  = sim_returns[int(n_sim * 0.95)]

        exp_wr   = sum(sim_wrs) / n_sim
        wr_std   = math.sqrt(sum((w - exp_wr) ** 2 for w in sim_wrs) / n_sim)

        ruin_prob = (ruin_count / n_simulations) * 100.0

        # Histograma de drawdowns (10 buckets para visualização)
        dd_histogram = _build_histogram(sim_drawdowns, n_buckets=10)

        report = MonteCarloReport(
            symbol          = symbol,
            pattern_key     = pattern_key,
            n_simulations   = n_simulations,
            n_trades        = n,
            dd_median       = round(p50, 3),
            dd_p95          = round(p95, 3),
            dd_p99          = round(p99, 3),
            dd_max_observed = round(max_obs, 3),
            ret_median      = round(ret_med, 3),
            ret_p5          = round(ret_p5, 3),
            ret_p95         = round(ret_p95, 3),
            ruin_threshold  = ruin_threshold,
            ruin_probability = round(ruin_prob, 2),
            expected_wr     = round(exp_wr, 2),
            wr_std          = round(wr_std, 2),
            dd_histogram    = dd_histogram,
            computed_at     = datetime.utcnow(),
        )

        if persist:
            await self._persist(report)

        return report

    async def _load_pnls(
        self,
        symbol:       Optional[str],
        pattern_key:  Optional[str],
        lookback_days: int,
    ) -> list[float]:
        """Carrega lista de pnl_pct dos trades resolvidos."""
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

            # Filtrar por pattern_key
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
                rows = filtered

            return [r.pnl_pct for r in rows if r.pnl_pct is not None]
        except Exception as e:
            logger.error("[mc] _load_pnls: %s", e)
            return []

    async def _persist(self, report: MonteCarloReport) -> None:
        """Persiste resultado no banco."""
        try:
            from app.models.robustness import MonteCarloResult
            async with AsyncSessionLocal() as db:
                obj = MonteCarloResult(
                    symbol           = report.symbol,
                    pattern_key      = report.pattern_key,
                    n_simulations    = report.n_simulations,
                    n_trades         = report.n_trades,
                    dd_median        = report.dd_median,
                    dd_p95           = report.dd_p95,
                    dd_p99           = report.dd_p99,
                    dd_max_observed  = report.dd_max_observed,
                    ret_median       = report.ret_median,
                    ret_p5           = report.ret_p5,
                    ret_p95          = report.ret_p95,
                    ruin_threshold   = report.ruin_threshold,
                    ruin_probability = report.ruin_probability,
                    expected_wr      = report.expected_wr,
                    wr_std           = report.wr_std,
                    dd_histogram_json = json.dumps(report.dd_histogram),
                    computed_at      = report.computed_at,
                )
                db.add(obj)
                await db.commit()
        except Exception as exc:
            logger.error("[mc] _persist: %s", exc)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_histogram(values: list[float], n_buckets: int = 10) -> dict:
    """Constrói histograma simples de frequências."""
    if not values:
        return {"bins": [], "counts": []}
    min_v  = values[0]
    max_v  = values[-1]
    if min_v == max_v:
        return {"bins": [min_v], "counts": [len(values)]}
    step   = (max_v - min_v) / n_buckets
    bins   = [round(min_v + i * step, 2) for i in range(n_buckets + 1)]
    counts = [0] * n_buckets
    for v in values:
        idx = min(int((v - min_v) / step), n_buckets - 1)
        counts[idx] += 1
    return {"bins": bins, "counts": counts}


# ── Singleton ─────────────────────────────────────────────────────────────────

monte_carlo_engine = MonteCarloEngine()
