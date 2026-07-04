"""
Fase 8 — Criterion Performance Engine
Calcula métricas individuais por critério a partir do signal_history.
Tudo determinístico, auditável, sem IA.
"""
from __future__ import annotations

import json
import math
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.analytics import SignalHistory, SignalOutcome

logger = logging.getLogger(__name__)

# ── Critérios canônicos (agrupados logicamente) ──────────────────────────────

# Mapeamento: nome_técnico → grupo_canônico
CRITERION_CANONICAL: dict[str, str] = {
    # EMA
    "ema_bull":          "ema_cross",
    "ema_bear":          "ema_cross",
    "ema_macro_bull":    "ema_macro",
    "ema_macro_bear":    "ema_macro",
    "ema_price_above":   "ema_price",
    "ema_price_below":   "ema_price",
    # MACD
    "macd_positive":     "macd_trend",
    "macd_negative":     "macd_trend",
    "macd_cross":        "macd_signal",
    "macd_cross_down":   "macd_signal",
    # RSI
    "rsi_ok":            "rsi",
    "rsi_high":          "rsi",
    # Structure
    "structure_bullish": "structure",
    "structure_bearish": "structure",
    "bos_bullish":       "bos",
    "bos_bearish":       "bos",
    # SR
    "price_near_support":    "sr_zone",
    "price_near_resistance": "sr_zone",
    # SMC
    "buy_side_sweep":         "sweep",
    "sell_side_sweep":        "sweep",
    "bullish_fvg":            "fvg",
    "bearish_fvg":            "fvg",
    "near_hvn_support":       "hvn_lvn",
    "near_lvn_resistance":    "hvn_lvn",
    "liq_score_strong_buy":   "liquidity",
    "liq_score_strong_sell":  "liquidity",
}

ALL_CANONICAL = sorted(set(CRITERION_CANONICAL.values()))


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class CriterionStats:
    """Métricas de performance para um critério."""
    criterion:     str
    sample_size:   int      = 0
    resolved:      int      = 0
    wins:          int      = 0
    losses:        int      = 0
    win_rate:      float    = 0.0   # 0–100
    profit_factor: float    = 0.0
    expectancy:    float    = 0.0   # média de pnl_pct quando resolvido
    sharpe:        float    = 0.0
    max_drawdown:  float    = 0.0   # maior sequência de perdas acumuladas %
    avg_win_pct:   float    = 0.0
    avg_loss_pct:  float    = 0.0
    regime_stats:  dict     = field(default_factory=dict)  # {regime: {wr, pf, n}}
    sufficient_data: bool   = False  # True se sample_size >= MIN_SAMPLE


@dataclass
class CriterionPerformanceReport:
    """Relatório completo de todos os critérios."""
    criteria:       list[CriterionStats]
    baseline_wr:    float   = 0.0   # win rate geral (todos os sinais)
    baseline_pf:    float   = 0.0   # profit factor geral
    baseline_exp:   float   = 0.0   # expectância geral
    total_resolved: int     = 0
    top_criteria:   list[str] = field(default_factory=list)
    worst_criteria: list[str] = field(default_factory=list)


# ── Constantes ────────────────────────────────────────────────────────────────

MIN_SAMPLE    = 5    # mínimo de trades resolvidos para ser significativo
LOOKBACK_DAYS = 90   # dias de histórico a considerar


# ── Engine ────────────────────────────────────────────────────────────────────

class CriterionPerformanceEngine:
    """Analisa performance de cada critério individualmente."""

    async def compute(
        self,
        symbol:       Optional[str] = None,
        lookback_days: int           = LOOKBACK_DAYS,
    ) -> CriterionPerformanceReport:
        """
        Lê signal_history, extrai critérios_met de cada sinal resolvido,
        e calcula métricas por critério canônico.
        """
        rows = await self._load_resolved_signals(symbol, lookback_days)
        if not rows:
            logger.info("[optimizer] Nenhum sinal resolvido encontrado.")
            return CriterionPerformanceReport(criteria=[], top_criteria=[], worst_criteria=[])

        # Baseline (todos os sinais)
        baseline = _compute_metrics(rows)

        # Agrupar por critério canônico
        criterion_rows: dict[str, list] = {c: [] for c in ALL_CANONICAL}

        for row in rows:
            if not row.criteria_met:
                continue
            try:
                criteria_list = json.loads(row.criteria_met)
            except (json.JSONDecodeError, TypeError):
                continue

            seen_canonical: set[str] = set()
            for crit in criteria_list:
                canonical = CRITERION_CANONICAL.get(crit)
                if canonical and canonical not in seen_canonical:
                    seen_canonical.add(canonical)
                    criterion_rows[canonical].append(row)

        # Calcular stats por critério
        stats_list: list[CriterionStats] = []
        for canonical in ALL_CANONICAL:
            c_rows = criterion_rows[canonical]
            stats = CriterionStats(criterion=canonical, sample_size=len(c_rows))
            if len(c_rows) >= 1:
                m = _compute_metrics(c_rows)
                stats.resolved      = m["resolved"]
                stats.wins          = m["wins"]
                stats.losses        = m["losses"]
                stats.win_rate      = m["win_rate"]
                stats.profit_factor = m["profit_factor"]
                stats.expectancy    = m["expectancy"]
                stats.sharpe        = m["sharpe"]
                stats.max_drawdown  = m["max_drawdown"]
                stats.avg_win_pct   = m["avg_win_pct"]
                stats.avg_loss_pct  = m["avg_loss_pct"]
                stats.regime_stats  = _compute_regime_breakdown(c_rows)
                stats.sufficient_data = stats.resolved >= MIN_SAMPLE
            stats_list.append(stats)

        # Ranking (apenas com dados suficientes)
        rankable = [s for s in stats_list if s.sufficient_data]
        rankable.sort(key=lambda s: s.profit_factor * (s.win_rate / 100), reverse=True)
        top     = [s.criterion for s in rankable[:5]]
        worst   = [s.criterion for s in rankable[-5:] if s.profit_factor < baseline["profit_factor"]]

        return CriterionPerformanceReport(
            criteria        = stats_list,
            baseline_wr     = baseline["win_rate"],
            baseline_pf     = baseline["profit_factor"],
            baseline_exp    = baseline["expectancy"],
            total_resolved  = baseline["resolved"],
            top_criteria    = top,
            worst_criteria  = worst,
        )

    async def _load_resolved_signals(
        self,
        symbol:        Optional[str],
        lookback_days: int,
    ) -> list:
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
            logger.error("[optimizer] _load_resolved_signals: %s", e)
            return []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_metrics(rows: list) -> dict:
    """Calcula win_rate, profit_factor, expectância, sharpe, drawdown de uma lista de sinais."""
    resolved = [r for r in rows if r.outcome in (SignalOutcome.WIN, SignalOutcome.LOSS) and r.pnl_pct is not None]
    if not resolved:
        return {
            "resolved": 0, "wins": 0, "losses": 0,
            "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
            "sharpe": 0.0, "max_drawdown": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
        }

    wins   = [r for r in resolved if r.outcome == SignalOutcome.WIN]
    losses = [r for r in resolved if r.outcome == SignalOutcome.LOSS]
    n = len(resolved)

    win_rate = len(wins) / n * 100.0

    gross_profit = sum(r.pnl_pct for r in wins)
    gross_loss   = abs(sum(r.pnl_pct for r in losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

    avg_win  = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    lr = 1.0 - (win_rate / 100.0)
    expectancy = (win_rate / 100.0) * avg_win - lr * avg_loss

    # Sharpe (anualizado assumindo 1 sinal/hora)
    pnls = [r.pnl_pct for r in resolved]
    mean_pnl = sum(pnls) / n
    if n > 1:
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / (n - 1)
        std_pnl  = math.sqrt(variance)
        sharpe   = (mean_pnl / std_pnl * math.sqrt(8760)) if std_pnl > 0 else 0.0
    else:
        sharpe = 0.0

    # Max Drawdown (sequência acumulada de perdas)
    max_dd = _compute_max_drawdown(pnls)

    return {
        "resolved": n, "wins": len(wins), "losses": len(losses),
        "win_rate": round(win_rate, 2), "profit_factor": round(profit_factor, 3),
        "expectancy": round(expectancy, 4), "sharpe": round(sharpe, 3),
        "max_drawdown": round(max_dd, 4), "avg_win_pct": round(avg_win, 4),
        "avg_loss_pct": round(avg_loss, 4),
    }


def _compute_max_drawdown(pnls: list[float]) -> float:
    """Calcula max drawdown (queda máxima de pico a vale) da curva de PnL acumulado."""
    if not pnls:
        return 0.0
    equity = 0.0
    peak   = 0.0
    max_dd = 0.0
    for p in pnls:
        equity += p
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _compute_regime_breakdown(rows: list) -> dict:
    """Separa métricas por regime de mercado."""
    regime_map: dict[str, list] = {}
    for r in rows:
        reg = str(r.regime.value) if r.regime else "UNKNOWN"
        regime_map.setdefault(reg, []).append(r)

    result = {}
    for reg, reg_rows in regime_map.items():
        m = _compute_metrics(reg_rows)
        result[reg] = {
            "n": m["resolved"], "win_rate": m["win_rate"],
            "profit_factor": m["profit_factor"], "expectancy": m["expectancy"],
        }
    return result


# ── Singleton ─────────────────────────────────────────────────────────────────

criterion_performance_engine = CriterionPerformanceEngine()
