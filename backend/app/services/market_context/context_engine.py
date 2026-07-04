"""
TradeAI - Context Engine (Fase 5)
Agrega todos os sinais de contexto em um Market Context Score (0-100).

Dimensões:
  news_score     (0-100): sentimento das últimas 24h de notícias
  fear_greed     (0-100): índice alternative.me (raw value já é 0-100)
  funding_score  (0-100): mapeado de rates negativos/positivos
  oi_score       (0-100): variação de OI (crescente = bullish)

Context Score Final = média ponderada das dimensões disponíveis.

Pesos:
  fear_greed: 35  (mais confiável e diretamente disponível)
  news:       30
  funding:    20
  oi:         15
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.services.news.news_store                import news_store
from app.services.market_context.fear_greed      import fear_greed_service
from app.services.market_context.funding_rate    import funding_rate_service
from app.services.market_context.open_interest   import open_interest_service
from app.logger import get_logger

logger = get_logger(__name__)

# Pesos das dimensões (devem somar 100)
CONTEXT_WEIGHTS = {
    "fear_greed": 35,
    "news":       30,
    "funding":    20,
    "oi":         15,
}


@dataclass
class ContextScore:
    symbol:         str
    news_score:     float         # 0-100
    fear_greed:     float         # 0-100 (valor bruto)
    fear_greed_label: str
    funding_score:  float         # 0-100
    funding_label:  str           # BULLISH | NEUTRAL | BEARISH
    oi_score:       float         # 0-100
    oi_change_pct:  Optional[float]  # variação percentual do OI
    context_score:  float         # 0-100 (score final)
    context_label:  str           # Bearish | Neutral | Bullish
    news_sentiment: dict          # {positive, neutral, negative, total}


def _funding_to_score(rate_pct: float | None) -> float:
    """Converte funding rate (%) em score 0-100."""
    if rate_pct is None:
        return 50.0
    # Rate típico: -0.05% a +0.05%
    # Mapeia [-0.1, +0.1] → [0, 100]
    normalized = (rate_pct + 0.1) / 0.2  # 0.0 a 1.0
    return max(0.0, min(100.0, normalized * 100))


def _oi_change_to_score(oi_change_pct: float | None) -> float:
    """Converte variação de OI em score 0-100."""
    if oi_change_pct is None:
        return 50.0
    # Variação típica: -5% a +5%
    # Mapeia [-10, +10] → [0, 100]
    normalized = (oi_change_pct + 10) / 20
    return max(0.0, min(100.0, normalized * 100))


def _score_to_label(score: float) -> str:
    if score >= 65: return "Bullish"
    if score <= 35: return "Bearish"
    return "Neutral"


class ContextEngine:

    async def calculate(self, symbol: str) -> ContextScore:
        """Calcula o Context Score completo para um símbolo."""

        # ── Coleta dados ──────────────────────────────────────────────────────
        news_summary   = await news_store.get_sentiment_summary(asset=symbol, hours=24)
        fg_latest      = await fear_greed_service.get_latest()
        fr_latest      = await funding_rate_service.get_latest(symbol)
        oi_change      = await open_interest_service.get_oi_change_pct(symbol)

        # ── Converte para scores 0-100 ─────────────────────────────────────
        news_score    = float(news_summary.get("news_score", 50.0))
        fg_value      = float(fg_latest.value) if fg_latest else 50.0
        fg_label      = fg_latest.classification if fg_latest else "Neutral"
        fr_pct        = fr_latest.rate_percent if fr_latest else None
        fr_label      = fr_latest.sentiment if fr_latest else "NEUTRAL"
        funding_score = _funding_to_score(fr_pct)
        oi_score      = _oi_change_to_score(oi_change)

        # ── Média ponderada ────────────────────────────────────────────────
        # Se não tiver dados, exclui da ponderação
        scores: dict[str, float] = {}
        weights: dict[str, int] = {}

        scores["fear_greed"] = fg_value
        weights["fear_greed"] = CONTEXT_WEIGHTS["fear_greed"]

        scores["news"] = news_score
        weights["news"] = CONTEXT_WEIGHTS["news"]

        if fr_latest is not None:
            scores["funding"] = funding_score
            weights["funding"] = CONTEXT_WEIGHTS["funding"]

        if oi_change is not None:
            scores["oi"] = oi_score
            weights["oi"] = CONTEXT_WEIGHTS["oi"]

        total_weight = sum(weights.values())
        if total_weight == 0:
            context_score = 50.0
        else:
            context_score = sum(
                scores[k] * weights[k] for k in scores
            ) / total_weight

        context_score = round(context_score, 1)

        return ContextScore(
            symbol          = symbol,
            news_score      = round(news_score, 1),
            fear_greed      = round(fg_value, 1),
            fear_greed_label = fg_label,
            funding_score   = round(funding_score, 1),
            funding_label   = fr_label,
            oi_score        = round(oi_score, 1),
            oi_change_pct   = round(oi_change, 2) if oi_change is not None else None,
            context_score   = context_score,
            context_label   = _score_to_label(context_score),
            news_sentiment  = {
                "positive": news_summary.get("positive", 0),
                "neutral":  news_summary.get("neutral",  0),
                "negative": news_summary.get("negative", 0),
                "total":    news_summary.get("total",    0),
            },
        )


context_engine = ContextEngine()
