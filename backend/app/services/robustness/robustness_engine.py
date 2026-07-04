"""
Fase 10 — Robustness Engine (Orquestrador)
Coordena Walk Forward, Monte Carlo e Stability Analyzer.
Calcula Robustness Score global (0-100).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.services.robustness.walk_forward import walk_forward_validator, WalkForwardReport
from app.services.robustness.monte_carlo  import monte_carlo_engine, MonteCarloReport
from app.services.robustness.stability    import strategy_stability_analyzer, StabilityReport

logger = logging.getLogger(__name__)


# ── Dataclass de resultado completo ───────────────────────────────────────────

@dataclass
class RobustnessReport:
    """Relatório completo de robustez da estratégia."""
    symbol:          Optional[str]  = None
    pattern_key:     Optional[str]  = None
    walk_forward:    Optional[WalkForwardReport] = None
    monte_carlo:     Optional[MonteCarloReport]  = None
    stability:       Optional[StabilityReport]   = None
    robustness_score: float         = 0.0        # 0-100 composto
    interpretation:  str            = ""
    computed_at:     datetime       = field(default_factory=datetime.utcnow)


# ── Engine ────────────────────────────────────────────────────────────────────

class RobustnessEngine:
    """
    Orquestra os três módulos de robustez e consolida um score global.
    Sem IA — puramente determinístico.
    """

    async def run(
        self,
        symbol:         Optional[str] = None,
        pattern_key:    Optional[str] = None,
        n_simulations:  int           = 5000,
        lookback_days:  int           = 90,
        persist:        bool          = True,
    ) -> RobustnessReport:
        """Executa análise completa de robustez."""
        logger.info("[robustness] iniciando análise symbol=%s pattern=%s", symbol, pattern_key)

        # Rodar os três módulos independentemente (sem paralelismo para manter determinismo)
        try:
            wf = await walk_forward_validator.validate(
                symbol=symbol, pattern_key=pattern_key, persist=persist,
            )
        except Exception as exc:
            logger.error("[robustness] walk_forward falhou: %s", exc)
            wf = None

        try:
            mc = await monte_carlo_engine.simulate(
                symbol=symbol, pattern_key=pattern_key,
                n_simulations=n_simulations,
                lookback_days=lookback_days, persist=persist,
            )
        except Exception as exc:
            logger.error("[robustness] monte_carlo falhou: %s", exc)
            mc = None

        try:
            st = await strategy_stability_analyzer.analyze(
                symbol=symbol, pattern_key=pattern_key,
                lookback_days=lookback_days, persist=persist,
            )
        except Exception as exc:
            logger.error("[robustness] stability falhou: %s", exc)
            st = None

        # Calcular score composto
        score, interpretation = _compute_robustness_score(wf, mc, st)

        report = RobustnessReport(
            symbol           = symbol,
            pattern_key      = pattern_key,
            walk_forward     = wf,
            monte_carlo      = mc,
            stability        = st,
            robustness_score = score,
            interpretation   = interpretation,
            computed_at      = datetime.utcnow(),
        )

        logger.info("[robustness] score=%.1f (%s)", score, interpretation)
        return report


# ── Score composto ────────────────────────────────────────────────────────────

def _compute_robustness_score(
    wf: Optional[WalkForwardReport],
    mc: Optional[MonteCarloReport],
    st: Optional[StabilityReport],
) -> tuple[float, str]:
    """
    Robustness Score (0-100) composto:
      - Walk Forward score:  40% do peso
      - Monte Carlo risk:    35% (100 - ruin_prob * k - dd_penalty)
      - Stability:           25%
    """
    components: list[tuple[float, float]] = []   # (score, weight)

    # ── Walk Forward (40%) ───────────────────────────────────────────────────
    if wf and wf.n_trades_total > 0:
        components.append((wf.wf_score, 0.40))

    # ── Monte Carlo (35%) ────────────────────────────────────────────────────
    if mc and mc.n_trades > 0:
        # Penalizar risco de ruína: cada % de risco = -2 pontos
        ruin_penalty = min(mc.ruin_probability * 2.0, 50.0)
        # Penalizar drawdown esperado alto (> 10%)
        dd_penalty   = max(0.0, (mc.dd_p95 - 10.0) * 1.5)
        mc_score     = max(0.0, 100.0 - ruin_penalty - dd_penalty)
        components.append((mc_score, 0.35))

    # ── Stability (25%) ──────────────────────────────────────────────────────
    if st and st.n_total_trades > 0:
        components.append((st.overall_stability_score, 0.25))

    if not components:
        return 0.0, "DADOS_INSUFICIENTES"

    # Normalizar pesos para o que foi calculado
    total_weight = sum(w for _, w in components)
    score = sum(s * (w / total_weight) for s, w in components)
    score = round(score, 1)

    if score >= 75:
        interpretation = "ROBUSTO"
    elif score >= 55:
        interpretation = "MODERADO"
    elif score >= 35:
        interpretation = "FRAGIL"
    else:
        interpretation = "ALTO_RISCO"

    return score, interpretation


# ── Singleton ─────────────────────────────────────────────────────────────────

robustness_engine = RobustnessEngine()
