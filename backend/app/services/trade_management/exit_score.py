"""
TradeAI — Exit Score Engine (Fase 12)

Score 0-100 baseado em:
  - Context Score (Fase 5)
  - Regime (Fase 6)
  - Market Structure (Fase 6.5)
  - Smart Money / Liquidity (Fase 7)
  - Momentum (P&L% atual)

Se Exit Score < paper_exit_score_threshold → close_reason = EXIT_SCORE

Determinístico — sem randomicidade.
"""

from __future__ import annotations

from typing import Optional, Any
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


def compute_exit_score(
    side: str,
    entry_price: float,
    current_price: float,
    context: Optional[Any] = None,
    regime: Optional[Any]  = None,
    structure: Optional[Any] = None,
    smc: Optional[Any] = None,
) -> float:
    """
    Calcula Exit Score 0-100 para o trade aberto.

    Componentes e pesos:
      Context Score  : 25%
      Regime         : 25%
      Structure      : 25%
      SMC            : 15%
      Momentum       : 10%

    Interpretação: score BAIXO = sinal de saída.
    """
    score = 50.0  # base neutro

    # ── Contexto de mercado (25%) ─────────────────────────────────────────────
    if context is not None:
        try:
            ctx_val = float(getattr(context, "context_score", 50.0) or 50.0)
            # context_score 0-100; neutro = 50
            ctx_delta = (ctx_val - 50.0) * 0.5  # ±25
            if side == "SHORT":
                ctx_delta = -ctx_delta  # inverter para SHORT
            score += ctx_delta
        except Exception as e:
            logger.warning(f"exit_score: {e}", exc_info=True)

    # ── Regime (25%) ─────────────────────────────────────────────────────────
    if regime is not None:
        try:
            regime_val = str(getattr(regime, "regime", "UNKNOWN"))
            if hasattr(regime_val, "value"):
                regime_val = regime_val.value
            regime_map = {
                "LONG": {"BULL": 20, "BEAR": -20, "SIDEWAYS": -5, "HIGH_VOLATILITY": -10},
                "SHORT": {"BULL": -20, "BEAR": 20, "SIDEWAYS": -5, "HIGH_VOLATILITY": -10},
            }
            delta = regime_map.get(side, {}).get(regime_val.upper(), 0)
            score += delta
        except Exception as e:
            logger.warning(f"exit_score: {e}", exc_info=True)

    # ── Market Structure (25%) ────────────────────────────────────────────────
    if structure is not None:
        try:
            trend = str(getattr(structure, "trend", "") or "")
            if side == "LONG":
                if trend == "BULLISH":
                    score += 15
                elif trend == "BEARISH":
                    score -= 20
                elif trend == "RANGING":
                    score -= 5
            else:  # SHORT
                if trend == "BEARISH":
                    score += 15
                elif trend == "BULLISH":
                    score -= 20
                elif trend == "RANGING":
                    score -= 5
            # BOS/CHoCH adverso
            if side == "LONG" and getattr(structure, "bos_bearish", False):
                score -= 10
            if side == "SHORT" and getattr(structure, "bos_bullish", False):
                score -= 10
        except Exception as e:
            logger.warning(f"exit_score: {e}", exc_info=True)

    # ── SMC / Liquidity (15%) ─────────────────────────────────────────────────
    if smc is not None:
        try:
            liq_score  = float(getattr(smc, "liquidity_score", 50.0) or 50.0)
            sweep_bias = str(getattr(smc, "sweep_bias", "") or "")
            liq_delta  = (liq_score - 50.0) * 0.1  # ±5
            if side == "SHORT":
                liq_delta = -liq_delta
            score += liq_delta

            if side == "LONG" and sweep_bias == "BEARISH":
                score -= 8
            elif side == "SHORT" and sweep_bias == "BULLISH":
                score -= 8
        except Exception as e:
            logger.warning(f"exit_score: {e}", exc_info=True)

    # ── Momentum: P&L atual (10%) ─────────────────────────────────────────────
    if entry_price and entry_price > 0:
        try:
            if side == "LONG":
                pnl_pct = (current_price - entry_price) / entry_price * 100
            else:
                pnl_pct = (entry_price - current_price) / entry_price * 100
            # ±10 pontos para ±10% P&L
            momentum_delta = max(-10, min(10, pnl_pct * 1.0))
            score += momentum_delta
        except Exception as e:
            logger.warning(f"exit_score: {e}", exc_info=True)

    return round(max(0.0, min(100.0, score)), 2)


def should_exit(exit_score: float) -> bool:
    """Retorna True se Exit Score está abaixo do threshold configurado."""
    return exit_score < settings.paper_exit_score_threshold
