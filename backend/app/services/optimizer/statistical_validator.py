"""
V7 — Statistical Validator (7.6)
Validação estatística de parâmetros, scores e critérios contra dados históricos.

Capacidades:
  1. Calibração do weighted_score: WR real vs score previsto
  2. Significância de critérios: chi-squared / G-test por critério
  3. Validação de ranges RSI: WR dentro vs fora do range calibrado
  4. Relatório consolidado com recomendações

Uso:
  validator = StatisticalValidator()
  report = await validator.validate(symbol=None, lookback_days=90)
  print(report.score_calibration)
  print(report.criterion_significance)
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
from app.services.optimizer.criterion_performance import CRITERION_CANONICAL, ALL_CANONICAL

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
MIN_SAMPLE_VALIDATION = 10  # mínimo de amostras para teste estatístico
SCORE_BINS = [0, 20, 40, 50, 60, 70, 80, 90, 100]  # faixas de score


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class BinStats:
    """Métricas de uma faixa de score."""
    bin_label:   str    # "0-20", "20-40", etc.
    count:       int    = 0
    wins:        int    = 0
    losses:      int    = 0
    win_rate:    float  = 0.0
    profit_factor: float = 0.0
    expectancy:  float  = 0.0   # pnl_pct médio
    avg_confidence: float = 0.0
    sharpe:      float  = 0.0


@dataclass
class ScoreCalibration:
    """
    Valida o weighted_score: scores mais altos devem produzir
    win rates e profit factors maiores.
    """
    bins:        list[BinStats] = field(default_factory=list)
    spearman_r:  float = 0.0    # correlação score vs WR (se bins suficientes)
    monotonic:   bool  = False   # WR é estritamente crescente com score?
    warning:     str   = ""


@dataclass
class CriterionSignificance:
    """
    Teste qui-quadrado para cada critério:
    - H0: WR do critério = WR geral (critério não discrimina)
    - Rejeitar H0 se p-value < 0.05 → critério é significativo
    """
    criterion:     str
    sample_size:   int     = 0
    wr_in:         float   = 0.0    # WR quando critério está presente
    wr_out:        float   = 0.0    # WR quando critério está ausente
    delta_wr:      float   = 0.0    # wr_in - wr_out
    chi2_stat:     float   = 0.0
    p_value:       float   = 1.0
    significant:   bool    = False  # p < 0.05
    recommended:   bool    = False  # wr_in > wr_out AND significant


@dataclass
class RsiRangeValidation:
    """
    Valida um range RSI calibrado comparando WR dentro vs fora do range.
    """
    range_label:   str     # "30-58" (LONG)
    side:          str     # LONG / SHORT
    sample_in:     int     = 0
    sample_out:    int     = 0
    wr_in:         float   = 0.0
    wr_out:        float   = 0.0
    delta_wr:      float   = 0.0
    optimal_range: str     = ""     # range sugerido com melhor WR
    is_calibrated: bool    = False  # True se range atual é o melhor


@dataclass
class ValidationReport:
    """Relatório consolidado de validação estatística."""
    score_calibration:     ScoreCalibration              = field(default_factory=ScoreCalibration)
    criterion_significance: list[CriterionSignificance]   = field(default_factory=list)
    rsi_validations:       list[RsiRangeValidation]      = field(default_factory=list)
    total_signals:         int  = 0
    resolved_signals:      int  = 0
    baseline_wr:           float = 0.0
    baseline_pf:           float = 0.0
    recommendations:       list[str] = field(default_factory=list)
    errors:                list[str] = field(default_factory=list)


# ── Helpers estatísticos ──────────────────────────────────────────────────────

def _chi2_gof(observed_in: int, total_in: int,
              observed_out: int, total_out: int,
              expected_wr: float) -> tuple[float, float]:
    """
    Teste G (log-likelihood ratio) para independência.
    Mais robusto que chi² clássico para amostras pequenas.
    Retorna (G_stat, p_value).
    """
    if total_in == 0 or total_out == 0:
        return 0.0, 1.0

    expected_in  = total_in  * expected_wr / 100
    expected_out = total_out * expected_wr / 100

    # Evitar log(0)
    def _safe_log_ratio(obs: float, exp: float) -> float:
        if obs <= 0 or exp <= 0:
            return 0.0
        return obs * math.log(obs / exp)

    g_stat = 2 * (
        _safe_log_ratio(observed_in, expected_in) +
        _safe_log_ratio(total_in - observed_in, total_in - expected_in) +
        _safe_log_ratio(observed_out, expected_out) +
        _safe_log_ratio(total_out - observed_out, total_out - expected_out)
    )

    # p-value da distribuição chi² com 1 grau de liberdade
    p_value = 1.0 - _chi2_cdf(g_stat, 1)
    return round(g_stat, 4), round(p_value, 4)


def _chi2_cdf(x: float, dof: int) -> float:
    """CDF aproximada da distribuição chi²."""
    if x <= 0:
        return 0.0
    # Aproximação usando série para dof = 1
    if dof == 1:
        return 2 * _normal_cdf(math.sqrt(x)) - 1
    return min(0.9999, 1.0 - math.exp(-x / 2))


def _normal_cdf(x: float) -> float:
    """CDF da normal padrão (aproximação de Abramowitz & Stegun)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pnl_net(r) -> float:
    """Retorna net_pnl_pct (fee-ajustado) se disponível, senão pnl_pct."""
    if hasattr(r, "net_pnl_pct") and r.net_pnl_pct is not None:
        return r.net_pnl_pct
    return r.pnl_pct or 0.0


def _compute_metrics_from_rows(rows: list) -> dict:
    """Calcula métricas básicas de uma lista de SignalHistory.
    Usa net_pnl_pct (fee-ajustado, V7.11) quando disponível.
    """
    if not rows:
        return {"resolved": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
                "sharpe": 0.0, "max_drawdown": 0.0,
                "net_win_rate": 0.0, "net_profit_factor": 0.0, "net_expectancy": 0.0}

    resolved = [r for r in rows if r.outcome in (SignalOutcome.WIN, SignalOutcome.LOSS)]
    if not resolved:
        return {"resolved": 0, "wins": 0, "losses": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0,
                "sharpe": 0.0, "max_drawdown": 0.0,
                "net_win_rate": 0.0, "net_profit_factor": 0.0, "net_expectancy": 0.0}

    wins   = [r for r in resolved if r.outcome == SignalOutcome.WIN]
    losses = [r for r in resolved if r.outcome == SignalOutcome.LOSS]
    wr     = len(wins) / len(resolved) * 100 if resolved else 0.0

    gains      = [abs(_pnl_net(r)) for r in wins]
    losses_pnl = [abs(_pnl_net(r)) for r in losses]
    avg_gain   = sum(gains) / len(gains) if gains else 0.0
    avg_loss   = sum(losses_pnl) / len(losses_pnl) if losses_pnl else 1.0
    pf         = avg_gain / avg_loss if avg_loss > 0 else 0.0
    exp        = sum(_pnl_net(r) for r in resolved) / len(resolved)

    # ── Net (reclassificado)
    net_wins   = [r for r in resolved if _pnl_net(r) > 0]
    net_losses = [r for r in resolved if _pnl_net(r) <= 0]
    nw = len(net_wins)
    nl_ = len(net_losses)
    net_wr = nw / len(resolved) * 100 if resolved else 0.0
    net_avg_win  = sum(_pnl_net(r) for r in net_wins) / nw if nw else 0.0
    net_avg_loss = sum(abs(_pnl_net(r)) for r in net_losses) / nl_ if nl_ else 1.0
    net_pf = net_avg_win / net_avg_loss if net_avg_loss > 0 else 0.0
    net_exp = sum(_pnl_net(r) for r in resolved) / len(resolved)

    # Sharpe aproximado
    pnl_values = [_pnl_net(r) for r in resolved]
    mean_pnl = sum(pnl_values) / len(pnl_values)
    variance = sum((p - mean_pnl) ** 2 for p in pnl_values) / len(pnl_values) if len(pnl_values) > 1 else 0
    sharpe   = mean_pnl / math.sqrt(variance) if variance > 0 else 0.0

    # Max drawdown (sequência de perdas consecutivas)
    dd = 0.0
    current_dd = 0.0
    for r in resolved:
        pnl = _pnl_net(r)
        if pnl < 0:
            current_dd += abs(pnl)
        else:
            dd = max(dd, current_dd)
            current_dd = 0.0
    dd = max(dd, current_dd)

    return {
        "resolved": len(resolved), "wins": len(wins), "losses": len(losses),
        "win_rate": round(wr, 2), "profit_factor": round(pf, 4),
        "expectancy": round(exp, 4), "sharpe": round(sharpe, 4),
        "max_drawdown": round(dd, 4),
        "net_win_rate": round(net_wr, 2), "net_profit_factor": round(net_pf, 4),
        "net_expectancy": round(net_exp, 4),
    }


# ── Statistical Validator ─────────────────────────────────────────────────────

class StatisticalValidator:
    """
    Valida estatisticamente parâmetros, scores e critérios
    contra dados históricos de signal_history.
    """

    async def validate(
        self,
        symbol: Optional[str] = None,
        lookback_days: int = 90,
    ) -> ValidationReport:
        """
        Roda validação completa e retorna relatório.
        """
        rows = await self._load_resolved_signals(symbol, lookback_days)
        if not rows:
            return ValidationReport(
                errors=["Nenhum sinal resolvido encontrado no período."]
            )

        baseline = _compute_metrics_from_rows(rows)
        report = ValidationReport(
            total_signals    = len(rows),
            resolved_signals = baseline["resolved"],
            baseline_wr      = baseline["win_rate"],
            baseline_pf      = baseline["profit_factor"],
        )

        try:
            report.score_calibration = self._calibrate_scores(rows)
        except Exception as e:
            report.errors.append(f"Score calibration: {e}")

        try:
            report.criterion_significance = await self._test_criterion_significance(
                rows, baseline["win_rate"]
            )
        except Exception as e:
            report.errors.append(f"Criterion significance: {e}")

        try:
            report.rsi_validations = self._validate_rsi_ranges(rows)
        except Exception as e:
            report.errors.append(f"RSI validation: {e}")

        # Gerar recomendações
        report.recommendations = self._generate_recommendations(report)

        return report

    # ── Load ──────────────────────────────────────────────────────────────────

    async def _load_resolved_signals(
        self, symbol: Optional[str] = None, lookback_days: int = 90
    ) -> list:
        """Carrega sinais resolvidos (WIN/LOSS) do banco."""
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        try:
            async with AsyncSessionLocal() as db:
                query = select(SignalHistory).where(
                    SignalHistory.emitted_at >= cutoff,
                    SignalHistory.outcome.in_([SignalOutcome.WIN, SignalOutcome.LOSS]),
                )
                if symbol:
                    query = query.where(SignalHistory.symbol == symbol)
                result = await db.execute(query.order_by(SignalHistory.emitted_at))
                return list(result.scalars().all())
        except Exception as e:
            logger.error("[validate] load: %s", e)
            return []

    # ── 1. Score Calibration ─────────────────────────────────────────────────

    def _calibrate_scores(self, rows: list) -> ScoreCalibration:
        """
        Agrupa sinais por faixa de weighted_score e mede WR real.
        Um sistema bem calibrado tem WR crescente com o score.
        """
        bins: list[BinStats] = []
        for i in range(len(SCORE_BINS) - 1):
            lo = SCORE_BINS[i]
            hi = SCORE_BINS[i + 1]
            label = f"{lo}-{hi}"

            in_bin = [
                r for r in rows
                if r.weighted_score is not None
                and lo <= r.weighted_score < (hi if hi < 100 else 101)
            ]
            if not in_bin:
                bins.append(BinStats(bin_label=label))
                continue

            m = _compute_metrics_from_rows(in_bin)
            avg_conf = sum(r.confidence or 0 for r in in_bin) / len(in_bin)
            bins.append(BinStats(
                bin_label      = label,
                count          = len(in_bin),
                wins           = m["wins"],
                losses         = m["losses"],
                win_rate       = m["win_rate"],
                profit_factor  = m["profit_factor"],
                expectancy     = m["expectancy"],
                avg_confidence = round(avg_conf, 1),
                sharpe         = m["sharpe"],
            ))

        # Verificar monotonicidade
        wr_values = [b.win_rate for b in bins if b.count > 0]
        monotonic = all(wr_values[i] <= wr_values[i + 1] for i in range(len(wr_values) - 1)) if len(wr_values) >= 2 else False

        # Spearman rank correlation (versão simplificada)
        spearman_r = 0.0
        if len(wr_values) >= 3:
            # Correlação entre rank do bin e WR
            ranks = list(range(1, len(wr_values) + 1))
            n = len(wr_values)
            d_sq = sum((ranks[i] - wr_values[i]) ** 2 for i in range(n))
            spearman_r = round(1 - (6 * d_sq) / (n * (n * n - 1)), 4)

        warning = ""
        if not monotonic:
            warning = "WR não é monotônico com score — calibração pode estar fraca."
        elif spearman_r < 0.5:
            warning = f"Correlação score-WR baixa (r={spearman_r}). Scores podem não refletir qualidade real."

        return ScoreCalibration(
            bins=bins, spearman_r=spearman_r,
            monotonic=monotonic, warning=warning,
        )

    # ── 2. Criterion Significance ────────────────────────────────────────────

    async def _test_criterion_significance(
        self, rows: list, baseline_wr: float
    ) -> list[CriterionSignificance]:
        """
        Para cada critério canônico, testa se sinais que o atenderam
        têm WR significativamente diferente da baseline.
        """
        # Agrupar por critério
        criterion_rows: dict[str, list] = {c: [] for c in ALL_CANONICAL}
        for row in rows:
            if not row.criteria_met:
                continue
            try:
                criteria_list = json.loads(row.criteria_met)
            except (json.JSONDecodeError, TypeError):
                continue
            seen = set()
            for crit in criteria_list:
                canonical = CRITERION_CANONICAL.get(crit)
                if canonical and canonical not in seen:
                    seen.add(canonical)
                    criterion_rows[canonical].append(row)

        results: list[CriterionSignificance] = []
        for criterion in ALL_CANONICAL:
            in_rows  = criterion_rows[criterion]
            out_rows = [r for r in rows if r not in in_rows]

            if len(in_rows) < MIN_SAMPLE_VALIDATION or len(out_rows) < MIN_SAMPLE_VALIDATION:
                results.append(CriterionSignificance(
                    criterion=criterion, sample_size=len(in_rows),
                    wr_in=0, wr_out=0, delta_wr=0,
                ))
                continue

            m_in  = _compute_metrics_from_rows(in_rows)
            m_out = _compute_metrics_from_rows(out_rows)

            g_stat, p_val = _chi2_gof(
                m_in["wins"], m_in["resolved"],
                m_out["wins"], m_out["resolved"],
                baseline_wr,
            )

            delta = round(m_in["win_rate"] - m_out["win_rate"], 2)
            results.append(CriterionSignificance(
                criterion     = criterion,
                sample_size   = m_in["resolved"],
                wr_in         = m_in["win_rate"],
                wr_out        = m_out["win_rate"],
                delta_wr      = delta,
                chi2_stat     = g_stat,
                p_value       = p_val,
                significant   = p_val < 0.05,
                recommended   = delta > 0 and p_val < 0.05,
            ))

        return results

    # ── 3. RSI Range Validation ─────────────────────────────────────────────

    def _validate_rsi_ranges(self, rows: list) -> list[RsiRangeValidation]:
        """
        Valida ranges RSI calibrados testando variações.
        Para cada range atual (LONG 30-58, SHORT 42-70, etc.),
        testa variações de ±5 e encontra o range com melhor WR.
        """
        # Ranges atuais por regime
        current_ranges = [
            ("30-58", "LONG", 30, 58),
            ("42-70", "SHORT", 42, 70),
            ("35-70", "LONG_1M", 35, 70),
            ("30-65", "SHORT_1M", 30, 65),
        ]

        results: list[RsiRangeValidation] = []
        for label, side, lo, hi in current_ranges:
            # Sinais com RSI disponível
            with_rsi = [r for r in rows if r.rsi is not None]
            if len(with_rsi) < MIN_SAMPLE_VALIDATION * 2:
                results.append(RsiRangeValidation(
                    range_label=label, side=side,
                    is_calibrated=False,
                ))
                continue

            in_range  = [r for r in with_rsi if lo <= r.rsi <= hi]
            out_range = [r for r in with_rsi if r.rsi < lo or r.rsi > hi]

            m_in  = _compute_metrics_from_rows(in_range)
            m_out = _compute_metrics_from_rows(out_range) if out_range else {"win_rate": 0}

            # Testar variações: shift de -10 a +10 no range
            best_wr = 0.0
            best_range = ""
            for shift in [-10, -5, 0, 5, 10]:
                test_lo = max(0, lo + shift)
                test_hi = min(100, hi + shift)
                if test_lo >= test_hi:
                    continue
                test_in = [r for r in with_rsi if test_lo <= r.rsi <= test_hi]
                if len(test_in) < MIN_SAMPLE_VALIDATION:
                    continue
                t = _compute_metrics_from_rows(test_in)
                if t["win_rate"] > best_wr:
                    best_wr = t["win_rate"]
                    best_range = f"{test_lo}-{test_hi}"

            results.append(RsiRangeValidation(
                range_label   = label,
                side          = side,
                sample_in     = m_in["resolved"],
                sample_out    = m_out["resolved"] if out_range else 0,
                wr_in         = m_in["win_rate"],
                wr_out        = m_out["win_rate"] if out_range else 0,
                delta_wr      = round(m_in["win_rate"] - (m_out["win_rate"] if out_range else 0), 2),
                optimal_range = best_range,
                is_calibrated = (best_range == f"{lo}-{hi}") or (best_range == ""),
            ))

        return results

    # ── 4. Recommendations ──────────────────────────────────────────────────

    def _generate_recommendations(self, report: ValidationReport) -> list[str]:
        """Gera recomendações acionáveis baseadas na validação."""
        recs: list[str] = []

        # Score calibration
        if not report.score_calibration.monotonic:
            recs.append("⚠️ Score calibration: WR não é monotônico. "
                        "Considere recalibrar os thresholds de BUY/SELL.")
        if report.score_calibration.spearman_r < 0.3:
            recs.append("⚠️ Score calibration: correlação score-WR muito baixa. "
                        "Scores podem não refletir qualidade real dos sinais.")

        # Significant criteria
        sig_count = sum(1 for c in report.criterion_significance if c.significant)
        weak_count = sum(1 for c in report.criterion_significance
                         if c.sample_size >= MIN_SAMPLE_VALIDATION and not c.significant)

        if sig_count < 3:
            recs.append(f"⚠️ Apenas {sig_count}/{len(report.criterion_significance)} critérios "
                        "são estatisticamente significativos. Considere revisar "
                        "ou remover critérios sem poder discriminatório.")
        if weak_count > len(report.criterion_significance) * 0.5:
            recs.append(f"⚠️ {weak_count} critérios não significativos. "
                        "Podem estar adicionando ruído ao sistema.")

        # Criteria to remove (negative delta and not significant)
        negative = [c for c in report.criterion_significance
                     if c.sample_size >= MIN_SAMPLE_VALIDATION and c.delta_wr < -5]
        if negative:
            recs.append(f"❌ Critérios com WR negativa: "
                        f"{', '.join(f'{c.criterion}({c.delta_wr:+.1f}% vs baseline)' for c in negative)}. "
                        "Considere reduzir seus pesos ou removê-los.")

        # RSI calibration
        for rsi in report.rsi_validations:
            if not rsi.is_calibrated and rsi.optimal_range:
                recs.append(f"🔧 RSI {rsi.range_label} ({rsi.side}): range ótimo sugerido "
                            f"'{rsi.optimal_range}' (atual WR={rsi.wr_in:.1f}%, "
                            f"fora={rsi.wr_out:.1f}%).")

        if not recs:
            recs.append("✅ Todos os parâmetros validados estão calibrados corretamente.")

        return recs


# ── Singleton ─────────────────────────────────────────────────────────────────
statistical_validator = StatisticalValidator()
