"""
TradeAI - Analysis Engine V2 (Fase 5)
Gera resumo técnico + contexto de mercado a partir de indicadores e dados externos.

Saídas técnicas:
  Trend, Momentum, Volatility (Fase 3)
Saídas de contexto (Fase 5):
  news_sentiment, fear_greed_label, funding_label, context_score
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
from app.models.indicators import MarketIndicator


# ── Tipos ─────────────────────────────────────────────────────────────────────

TrendLabel      = Literal["Strong Bullish", "Bullish", "Sideways", "Bearish", "Strong Bearish"]
MomentumLabel   = Literal["Strong", "Neutral", "Weak"]
VolatilityLabel = Literal["Low", "Medium", "High"]


@dataclass
class AnalysisResult:
    # ── Fase 3: Técnico ──────────────────────────────────────────────────────
    trend:      TrendLabel
    momentum:   MomentumLabel
    volatility: VolatilityLabel

    # ── Fase 5: Contexto externo (preenchido opcionalmente pelo caller) ───────
    news_sentiment:    Optional[str]   = field(default=None)   # POSITIVE|NEUTRAL|NEGATIVE
    fear_greed_label:  Optional[str]   = field(default=None)   # Extreme Fear..Extreme Greed
    fear_greed_value:  Optional[float] = field(default=None)   # 0-100
    funding_label:     Optional[str]   = field(default=None)   # BULLISH|NEUTRAL|BEARISH
    context_score:     Optional[float] = field(default=None)   # 0-100
    context_label:     Optional[str]   = field(default=None)   # Bearish|Neutral|Bullish

    # ── Fase 6+: IA ───────────────────────────────────────────────────────────
    # ai_confidence: Optional[float] = field(default=None)


# ── Engine ─────────────────────────────────────────────────────────────────────

def analyze(
    indicator:     MarketIndicator,
    current_price: float,
    context=None,   # ContextScore | None — injetado pela Fase 5
) -> AnalysisResult:
    """
    Gera resumo técnico e, quando disponível, enriquece com dados de contexto.

    Parâmetros:
        indicator:     Registro mais recente de MarketIndicator.
        current_price: Preço atual do ativo (para cálculo de ATR%).
        context:       ContextScore opcional (Fase 5+).
    """
    result = AnalysisResult(
        trend      = _determine_trend(indicator),
        momentum   = _determine_momentum(indicator),
        volatility = _determine_volatility(indicator, current_price),
    )

    # Enriquece com contexto externo (Fase 5)
    if context is not None:
        # news_sentiment vem do score: >60 POSITIVE, <40 NEGATIVE
        if context.news_score >= 60:
            result.news_sentiment = "POSITIVE"
        elif context.news_score <= 40:
            result.news_sentiment = "NEGATIVE"
        else:
            result.news_sentiment = "NEUTRAL"

        result.fear_greed_label = context.fear_greed_label
        result.fear_greed_value = context.fear_greed
        result.funding_label    = context.funding_label
        result.context_score    = context.context_score
        result.context_label    = context.context_label

    return result


# ── Trend ─────────────────────────────────────────────────────────────────────

def _determine_trend(ind: MarketIndicator) -> TrendLabel:
    """
    Analisa o alinhamento das EMAs para determinar a tendência.

    Strong Bullish: EMA9 > EMA21 > EMA50 > EMA200
    Bullish:        EMA9 > EMA21 > EMA50
    Bearish:        EMA9 < EMA21 < EMA50
    Strong Bearish: EMA9 < EMA21 < EMA50 < EMA200
    Sideways:       EMAs sem alinhamento consistente
    """
    e9, e21, e50, e200 = ind.ema_9, ind.ema_21, ind.ema_50, ind.ema_200

    if e9 is None or e21 is None or e50 is None:
        return "Sideways"

    bullish_short = e9  > e21 and e21 > e50
    bearish_short = e9  < e21 and e21 < e50

    if bullish_short:
        if e200 is not None and e50 > e200:
            return "Strong Bullish"
        return "Bullish"

    if bearish_short:
        if e200 is not None and e50 < e200:
            return "Strong Bearish"
        return "Bearish"

    return "Sideways"


# ── Momentum ──────────────────────────────────────────────────────────────────

def _determine_momentum(ind: MarketIndicator) -> MomentumLabel:
    """
    Avalia momentum combinando RSI e MACD.

    Strong: RSI > 60 AND MACD > 0 AND histogram > 0
    Weak:   RSI < 40 AND MACD < 0 AND histogram < 0
    Neutral: todos os demais casos
    """
    rsi  = ind.rsi
    macd = ind.macd
    hist = ind.macd_histogram

    if rsi is None:
        return "Neutral"

    # Contagem de sinais bullish
    bullish_signals = sum([
        rsi > 60,
        macd is not None and macd > 0,
        hist is not None and hist > 0,
    ])

    # Contagem de sinais bearish
    bearish_signals = sum([
        rsi < 40,
        macd is not None and macd < 0,
        hist is not None and hist < 0,
    ])

    if bullish_signals >= 2:
        return "Strong"
    if bearish_signals >= 2:
        return "Weak"
    return "Neutral"


# ── Volatility ────────────────────────────────────────────────────────────────

def _determine_volatility(ind: MarketIndicator, price: float) -> VolatilityLabel:
    """
    Calcula volatilidade como ATR% do preço.

    Low:    ATR% < 0.8%
    Medium: 0.8% ≤ ATR% ≤ 2.5%
    High:   ATR% > 2.5%
    """
    if ind.atr is None or price <= 0:
        return "Medium"

    atr_pct = (ind.atr / price) * 100.0

    if atr_pct < 0.8:
        return "Low"
    if atr_pct > 2.5:
        return "High"
    return "Medium"
