"""
Fase 9 — Alpha Pattern Engine
Analisa automaticamente todo o histórico de sinais para descobrir:
  1. Quais critérios individuais aumentam a taxa de acerto
  2. Quais combinações de 2-3 critérios funcionam melhor
  3. Quais padrões recorrentes geram prejuízo
Tudo determinístico, auditável, sem IA generativa.
"""
from __future__ import annotations

import json
import math
import logging
import itertools
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, delete
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome, MarketRegimeType
from app.models.alpha import AlphaPattern, AlphaPatternStats
from app.services.optimizer.criterion_performance import (
    CRITERION_CANONICAL, _compute_metrics, _compute_max_drawdown
)

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────

MIN_SAMPLE      = 5     # mínimo de sinais resolvidos para um padrão ser válido
MAX_COMBO_SIZE  = 3     # combinações até 3 critérios
TOP_N_BEST      = 20    # top N padrões positivos
TOP_N_WORST     = 10    # top N padrões negativos
LOOKBACK_DAYS   = 90    # janela de análise
SCORE_WR_WEIGHT = 0.5   # peso da win rate no alpha_score
SCORE_PF_WEIGHT = 0.35  # peso do profit factor
SCORE_N_WEIGHT  = 0.15  # peso da amostragem (log)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class PatternStats:
    """Resultado de análise para um padrão (critério único ou combinação)."""
    pattern_key:    str
    criteria:       list[str]
    criteria_count: int     = 1
    symbol:         Optional[str] = None
    regime:         Optional[str] = None
    trade_side:     Optional[str] = None
    sample_size:    int     = 0
    resolved:       int     = 0
    wins:           int     = 0
    losses:         int     = 0
    win_rate:       float   = 0.0
    profit_factor:  float   = 0.0
    expectancy:     float   = 0.0
    sharpe:         float   = 0.0
    max_drawdown:   float   = 0.0
    avg_win_pct:    float   = 0.0
    avg_loss_pct:   float   = 0.0
    alpha_score:    float   = 0.0   # 0-100
    is_positive:    bool    = True
    sufficient_data: bool   = False


@dataclass
class AlphaReport:
    """Relatório completo da análise alpha."""
    computed_at:     datetime         = field(default_factory=datetime.utcnow)
    symbol:          Optional[str]    = None
    total_resolved:  int              = 0
    baseline_wr:     float            = 0.0
    baseline_pf:     float            = 0.0
    baseline_exp:    float            = 0.0
    # Padrões positivos (alpha)
    best_patterns:   list[PatternStats] = field(default_factory=list)
    # Padrões negativos
    worst_patterns:  list[PatternStats] = field(default_factory=list)
    # Padrões únicos (1 critério)
    single_criteria: list[PatternStats] = field(default_factory=list)
    # Combinações (2-3 critérios)
    combinations:    list[PatternStats] = field(default_factory=list)


# ── Pattern Engine ────────────────────────────────────────────────────────────

class AlphaPatternEngine:
    """
    Descobre padrões de vantagem estatística no histórico de sinais.
    Totalmente determinístico — sem IA.
    """

    async def compute(
        self,
        symbol:        Optional[str] = None,
        lookback_days: int           = LOOKBACK_DAYS,
        persist:       bool          = True,
    ) -> AlphaReport:
        """Executa análise completa e retorna AlphaReport."""
        rows = await self._load_resolved(symbol, lookback_days)
        if not rows:
            logger.info("[alpha] Nenhum sinal resolvido para análise.")
            return AlphaReport(symbol=symbol, computed_at=datetime.utcnow())

        baseline = _compute_metrics(rows)

        # ── Critérios únicos ──────────────────────────────────────────────
        single = self._analyze_single_criteria(rows)

        # ── Combinações 2-3 ───────────────────────────────────────────────
        combos = self._analyze_combinations(rows)

        # ── Merge e ranking ───────────────────────────────────────────────
        all_patterns = single + combos
        for p in all_patterns:
            p.symbol = symbol

        best    = sorted(
            [p for p in all_patterns if p.sufficient_data and p.profit_factor >= baseline["profit_factor"] and p.win_rate >= baseline["win_rate"]],
            key=lambda p: p.alpha_score, reverse=True
        )[:TOP_N_BEST]

        worst   = sorted(
            [p for p in all_patterns if p.sufficient_data and (p.profit_factor < 0.9 or p.win_rate < 40.0)],
            key=lambda p: p.alpha_score
        )[:TOP_N_WORST]

        for p in worst:
            p.is_positive = False

        report = AlphaReport(
            computed_at     = datetime.utcnow(),
            symbol          = symbol,
            total_resolved  = baseline["resolved"],
            baseline_wr     = baseline["win_rate"],
            baseline_pf     = baseline["profit_factor"],
            baseline_exp    = baseline["expectancy"],
            best_patterns   = best,
            worst_patterns  = worst,
            single_criteria = sorted(single, key=lambda p: p.alpha_score, reverse=True),
            combinations    = sorted(combos, key=lambda p: p.alpha_score, reverse=True),
        )

        if persist:
            await self._persist(report)

        return report

    # ── Análise de critérios únicos ───────────────────────────────────────

    def _analyze_single_criteria(self, rows: list) -> list[PatternStats]:
        """Calcula métricas para cada critério técnico individual."""
        # Mapear critérios técnicos → canônicos
        canonical_rows: dict[str, list] = {}

        for row in rows:
            if not row.criteria_met:
                continue
            try:
                criteria_list = json.loads(row.criteria_met)
            except (json.JSONDecodeError, TypeError):
                continue

            seen: set[str] = set()
            for crit in criteria_list:
                # Usar nome técnico diretamente (mais granular que canônico)
                if crit and crit not in seen:
                    seen.add(crit)
                    canonical_rows.setdefault(crit, []).append(row)

        results = []
        for crit, crit_rows in canonical_rows.items():
            if len(crit_rows) < 1:
                continue
            m = _compute_metrics(crit_rows)
            score = _alpha_score(m["win_rate"], m["profit_factor"], m["resolved"])
            p = PatternStats(
                pattern_key    = crit,
                criteria       = [crit],
                criteria_count = 1,
                sample_size    = len(crit_rows),
                resolved       = m["resolved"],
                wins           = m["wins"],
                losses         = m["losses"],
                win_rate       = m["win_rate"],
                profit_factor  = m["profit_factor"],
                expectancy     = m["expectancy"],
                sharpe         = m["sharpe"],
                max_drawdown   = m["max_drawdown"],
                avg_win_pct    = m["avg_win_pct"],
                avg_loss_pct   = m["avg_loss_pct"],
                alpha_score    = score,
                sufficient_data = m["resolved"] >= MIN_SAMPLE,
            )
            results.append(p)

        return results

    # ── Análise de combinações ────────────────────────────────────────────

    def _analyze_combinations(self, rows: list) -> list[PatternStats]:
        """Analisa combinações de 2-3 critérios presentes simultaneamente."""
        # Extrair critérios por sinal
        signal_criteria: list[frozenset] = []
        for row in rows:
            if not row.criteria_met:
                continue
            try:
                criteria_list = json.loads(row.criteria_met)
            except (json.JSONDecodeError, TypeError):
                continue
            if criteria_list:
                signal_criteria.append(frozenset(criteria_list))

        if not signal_criteria:
            return []

        # Coletar todos os critérios únicos
        all_criteria = set()
        for sc in signal_criteria:
            all_criteria.update(sc)

        # Filtrar só critérios com sample suficiente (aparecem >= MIN_SAMPLE vezes)
        crit_count = {}
        for sc in signal_criteria:
            for c in sc:
                crit_count[c] = crit_count.get(c, 0) + 1
        frequent_criteria = [c for c, n in crit_count.items() if n >= MIN_SAMPLE]

        results = []
        combo_rows_cache: dict[frozenset, list] = {}

        for size in range(2, MAX_COMBO_SIZE + 1):
            for combo in itertools.combinations(sorted(frequent_criteria), size):
                combo_set = frozenset(combo)
                # Sinais que contêm TODOS os critérios da combinação
                combo_rows = [
                    rows[i] for i, sc in enumerate(signal_criteria)
                    if combo_set.issubset(sc)
                ]
                if len(combo_rows) < MIN_SAMPLE:
                    continue

                key = "|".join(sorted(combo))
                m = _compute_metrics(combo_rows)
                score = _alpha_score(m["win_rate"], m["profit_factor"], m["resolved"])
                p = PatternStats(
                    pattern_key    = key,
                    criteria       = list(combo),
                    criteria_count = size,
                    sample_size    = len(combo_rows),
                    resolved       = m["resolved"],
                    wins           = m["wins"],
                    losses         = m["losses"],
                    win_rate       = m["win_rate"],
                    profit_factor  = m["profit_factor"],
                    expectancy     = m["expectancy"],
                    sharpe         = m["sharpe"],
                    max_drawdown   = m["max_drawdown"],
                    avg_win_pct    = m["avg_win_pct"],
                    avg_loss_pct   = m["avg_loss_pct"],
                    alpha_score    = score,
                    sufficient_data = True,
                )
                results.append(p)

        return results

    # ── Persistência ──────────────────────────────────────────────────────

    async def _persist(self, report: AlphaReport) -> None:
        """Persiste padrões no banco de dados."""
        all_patterns = report.single_criteria + report.combinations
        if not all_patterns:
            return
        try:
            async with AsyncSessionLocal() as db:
                for p in all_patterns:
                    if not p.sufficient_data:
                        continue
                    # Upsert via merge
                    existing = await db.execute(
                        select(AlphaPattern).where(AlphaPattern.pattern_key == p.pattern_key)
                    )
                    obj = existing.scalar_one_or_none()
                    if obj is None:
                        obj = AlphaPattern(
                            pattern_key     = p.pattern_key,
                            criteria        = json.dumps(p.criteria),
                            criteria_count  = p.criteria_count,
                            symbol          = p.symbol,
                        )
                        db.add(obj)
                    # Atualizar métricas
                    obj.sample_size    = p.sample_size
                    obj.resolved       = p.resolved
                    obj.wins           = p.wins
                    obj.losses         = p.losses
                    obj.win_rate       = p.win_rate
                    obj.profit_factor  = p.profit_factor
                    obj.expectancy     = p.expectancy
                    obj.sharpe         = p.sharpe
                    obj.max_drawdown   = p.max_drawdown
                    obj.avg_win_pct    = p.avg_win_pct
                    obj.avg_loss_pct   = p.avg_loss_pct
                    obj.alpha_score    = p.alpha_score
                    obj.is_positive    = p.is_positive
                    obj.sufficient_data = p.sufficient_data
                    obj.last_updated   = datetime.utcnow()

                    # Snapshot histórico
                    snap = AlphaPatternStats(
                        pattern_key  = p.pattern_key,
                        symbol       = p.symbol,
                        sample_size  = p.sample_size,
                        win_rate     = p.win_rate,
                        profit_factor = p.profit_factor,
                        expectancy   = p.expectancy,
                        alpha_score  = p.alpha_score,
                        computed_at  = report.computed_at,
                    )
                    db.add(snap)

                await db.commit()
                logger.info("[alpha] %d padrões persistidos.", len(all_patterns))
        except Exception as exc:
            logger.error("[alpha] _persist error: %s", exc)

    # ── Loader ────────────────────────────────────────────────────────────

    async def _load_resolved(
        self,
        symbol:        Optional[str],
        lookback_days: int,
    ) -> list:
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
                if symbol:
                    q = q.where(SignalHistory.symbol == symbol)
                result = await db.execute(q)
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[alpha] _load_resolved: %s", e)
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _alpha_score(win_rate: float, profit_factor: float, n: int) -> float:
    """
    Score composto 0-100:
      - 50% win rate normalizada (0-100 → 0-50)
      - 35% profit factor normalizado (0-3+ → 0-35)
      - 15% peso da amostragem log(n) normalizado
    """
    wr_contrib  = min(win_rate, 100.0) * SCORE_WR_WEIGHT   # max 50
    pf_norm     = min(profit_factor / 3.0, 1.0)            # normaliza 0-3 → 0-1
    pf_contrib  = pf_norm * 100.0 * SCORE_PF_WEIGHT        # max 35
    n_norm      = min(math.log1p(n) / math.log1p(100), 1.0)
    n_contrib   = n_norm * 100.0 * SCORE_N_WEIGHT          # max 15
    return round(wr_contrib + pf_contrib + n_contrib, 2)


# ── Singleton ─────────────────────────────────────────────────────────────────

alpha_pattern_engine = AlphaPatternEngine()
