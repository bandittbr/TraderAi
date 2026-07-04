"""
Classificador determinístico de regime de mercado — Phase 6

Regimes detectados:
  BULL            — tendência de alta sustentada
  BEAR            — tendência de baixa sustentada
  SIDEWAYS        — mercado lateral, sem tendência clara
  HIGH_VOLATILITY — volatilidade acima do limiar independente do viés

Inputs necessários (duck-typed, aceita ORM ou snapshot):
  indicator.rsi, .ema_9, .ema_21, .ema_50, .ema_200, .atr
  current_price: float
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.analytics import MarketRegimeType


# ─────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────

HIGH_VOL_ATR_PCT        = 3.0    # ATR/price > 3% = alta volatilidade
BULL_EMA_MIN_SCORE      = 3      # EMA alignment score mínimo para BULL  (máx 4)
BEAR_EMA_MAX_SCORE      = -3     # EMA alignment score máximo para BEAR  (mín -4)
SIDEWAYS_ATR_MAX_PCT    = 1.5    # ATR/price < 1.5% reforça sideways
SIDEWAYS_EMA_ABS_MAX    = 2      # |score| ≤ 2 = EMAs intercaladas
BULL_PRICE_EMA200_PCT   = 0.0    # price > EMA200*(1+0%) para considerar bull
BEAR_PRICE_EMA200_PCT   = 0.0    # price < EMA200*(1-0%) para considerar bear


# ─────────────────────────────────────────────
# Resultado
# ─────────────────────────────────────────────

@dataclass
class RegimeResult:
    regime:               MarketRegimeType = MarketRegimeType.UNKNOWN
    confidence:           float            = 0.0        # 0–100
    ema_alignment_score:  float            = 0.0        # -4 a +4
    atr_pct:              float            = 0.0        # ATR / price * 100
    price_vs_ema200_pct:  float            = 0.0        # (price - EMA200) / EMA200 * 100
    ema9_vs_ema21_pct:    float            = 0.0
    rsi:                  float            = 50.0
    reasons:              list[str]        = field(default_factory=list)


# ─────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────

def _ema_alignment_score(ema_9: float, ema_21: float,
                          ema_50: float, ema_200: float) -> float:
    """
    Retorna score de -4 a +4:
      +1 por cada par EMA[n] > EMA[n+1] na direção bull
      -1 por cada par EMA[n] < EMA[n+1] na direção bear

    Pares avaliados: (9>21), (21>50), (50>200), (9>200)
    """
    score = 0.0
    if ema_9   > ema_21:  score += 1.0
    else:                 score -= 1.0
    if ema_21  > ema_50:  score += 1.0
    else:                 score -= 1.0
    if ema_50  > ema_200: score += 1.0
    else:                 score -= 1.0
    if ema_9   > ema_200: score += 1.0
    else:                 score -= 1.0
    return score


def _atr_pct(atr: float, price: float) -> float:
    """ATR como percentual do preço atual."""
    if price <= 0:
        return 0.0
    return (atr / price) * 100.0


def _pct_diff(a: float, b: float) -> float:
    """(a - b) / b * 100, evita divisão por zero."""
    if b == 0:
        return 0.0
    return ((a - b) / b) * 100.0


# ─────────────────────────────────────────────
# Classificador principal
# ─────────────────────────────────────────────

def classify_regime(indicator: Any, current_price: float) -> RegimeResult:
    """
    Classifica o regime de mercado de forma determinística.

    Ordem de prioridade:
      1. HIGH_VOLATILITY — ATR% acima do limiar (sobreposição possível)
      2. BULL  — EMA alignment forte + price > EMA200
      3. BEAR  — EMA alignment forte negativo + price < EMA200
      4. SIDEWAYS — caso padrão

    Args:
        indicator: objeto com atributos rsi, ema_9, ema_21, ema_50, ema_200, atr
        current_price: preço atual do ativo

    Returns:
        RegimeResult com regime, confiança e métricas de suporte
    """
    # Extrair valores com fallbacks seguros
    rsi    = float(getattr(indicator, "rsi",    50.0) or 50.0)
    ema_9  = float(getattr(indicator, "ema_9",  current_price) or current_price)
    ema_21 = float(getattr(indicator, "ema_21", current_price) or current_price)
    ema_50 = float(getattr(indicator, "ema_50", current_price) or current_price)
    ema_200 = float(getattr(indicator, "ema_200", current_price) or current_price)
    atr    = float(getattr(indicator, "atr",    0.0) or 0.0)

    price = current_price if current_price > 0 else 1.0

    # Calcular métricas de suporte
    ema_score        = _ema_alignment_score(ema_9, ema_21, ema_50, ema_200)
    atr_pct_val      = _atr_pct(atr, price)
    price_vs_200     = _pct_diff(price, ema_200)
    ema9_vs_ema21    = _pct_diff(ema_9, ema_21)
    reasons          = []

    # ─── 1. Verificar Alta Volatilidade ──────────────────────
    # ATR% acima do limiar → HIGH_VOLATILITY (pode coexistir com tendência)
    high_vol = atr_pct_val >= HIGH_VOL_ATR_PCT
    if high_vol:
        reasons.append(f"ATR={atr_pct_val:.2f}% >= {HIGH_VOL_ATR_PCT}%")

    # ─── 2. Calcular confiança base por EMA score ──────────────
    # score +4 = 100% bull, score -4 = 100% bear, 0 = 50%
    ema_confidence = 50.0 + (ema_score / 4.0) * 50.0

    # ─── 3. Classificar tendência ─────────────────────────────
    if ema_score >= BULL_EMA_MIN_SCORE and price_vs_200 > BULL_PRICE_EMA200_PCT:
        # BULL: EMAs alinhadas para cima + preço acima de EMA200
        reasons.append(f"EMA alignment={ema_score:.0f}/4")
        reasons.append(f"Price {price_vs_200:+.2f}% vs EMA200")
        if rsi > 50:
            reasons.append(f"RSI={rsi:.1f} > 50")
            ema_confidence = min(100.0, ema_confidence + 10.0)

        trend_regime = MarketRegimeType.BULL
        trend_confidence = ema_confidence

    elif ema_score <= BEAR_EMA_MAX_SCORE and price_vs_200 < -BEAR_PRICE_EMA200_PCT:
        # BEAR: EMAs alinhadas para baixo + preço abaixo de EMA200
        reasons.append(f"EMA alignment={ema_score:.0f}/4")
        reasons.append(f"Price {price_vs_200:+.2f}% vs EMA200")
        if rsi < 50:
            reasons.append(f"RSI={rsi:.1f} < 50")
            ema_confidence = min(100.0, ema_confidence + 10.0)

        trend_regime = MarketRegimeType.BEAR
        trend_confidence = 100.0 - ema_confidence  # inverte para bear

    else:
        # SIDEWAYS: EMAs intercaladas, sem tendência clara
        reasons.append(f"EMA alignment={ema_score:.0f} (indeciso)")
        if atr_pct_val <= SIDEWAYS_ATR_MAX_PCT:
            reasons.append(f"ATR={atr_pct_val:.2f}% (baixa volatilidade)")

        trend_regime = MarketRegimeType.SIDEWAYS
        # Confiança sideways: quanto mais próximo de 0 o ema_score, mais confiante
        sideways_conf = 50.0 + (1.0 - abs(ema_score) / 4.0) * 50.0
        trend_confidence = sideways_conf

    # ─── 4. HIGH_VOLATILITY sobrescreve quando ATR muito elevado ─────
    if high_vol and atr_pct_val >= HIGH_VOL_ATR_PCT * 1.5:
        # ATR >= 4.5% → HIGH_VOLATILITY independente da tendência
        final_regime = MarketRegimeType.HIGH_VOLATILITY
        final_confidence = min(100.0, 50.0 + (atr_pct_val - HIGH_VOL_ATR_PCT) * 20.0)
        reasons.insert(0, "ATR extremo sobrescreve tendência")
    elif high_vol:
        # ATR entre 3% e 4.5% → HIGH_VOLATILITY com menor confiança
        final_regime = MarketRegimeType.HIGH_VOLATILITY
        final_confidence = min(100.0, 50.0 + (atr_pct_val - HIGH_VOL_ATR_PCT) * 10.0)
    else:
        final_regime = trend_regime
        final_confidence = trend_confidence

    return RegimeResult(
        regime               = final_regime,
        confidence           = round(final_confidence, 1),
        ema_alignment_score  = ema_score,
        atr_pct              = round(atr_pct_val, 3),
        price_vs_ema200_pct  = round(price_vs_200, 3),
        ema9_vs_ema21_pct    = round(ema9_vs_ema21, 3),
        rsi                  = rsi,
        reasons              = reasons,
    )
