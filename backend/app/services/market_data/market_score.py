"""
TradeAI - Market Score Engine V2 (Fase 3)
Calcula um score 0–100 dividido em 4 dimensões:

  Trend Score      (0–35): alinhamento de EMAs + MACD
  Momentum Score   (0–25): posição do RSI + direção do MACD
  Volume Score     (0–25): volume atual vs. volume médio
  Volatility Score (0–15): ATR% vs. faixa ideal

Fallback por candles quando indicadores não estão disponíveis.

Pesos somam 100 e são facilmente ajustáveis.
Fase 4+: adicionar news_score, sentiment_score (via SCORE_WEIGHTS).
"""

from dataclasses import dataclass
from typing import Optional
from app.models.market import MarketCandle
from app.models.indicators import MarketIndicator
from app.logger import get_logger

logger = get_logger(__name__)

# ── Pesos ─────────────────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "trend":      35,  # alinhamento EMA / SMA
    "momentum":   25,  # RSI + MACD
    "volume":     25,  # volume relativo
    "volatility": 15,  # ATR% / range de candle
    # "news":     0,   # Fase 4+
    # "sentiment":0,   # Fase 4+
    # "funding":  0,   # Fase 5+
    # "ai":       0,   # Fase 6+
}

MIN_CANDLES   = 5
IDEAL_CANDLES = 20


@dataclass
class ScoreDetail:
    """Score V2 com detalhamento por dimensão."""
    symbol:           str
    total_score:      int
    trend_score:      float
    momentum_score:   float
    volume_score:     float
    volatility_score: float
    candles_used:     int


# ── Função principal ──────────────────────────────────────────────────────────

def calculate_market_score(
    candles:    list[MarketCandle],
    indicator:  Optional[MarketIndicator] = None,
    symbol:     str = "UNKNOWN",
) -> ScoreDetail:
    """
    Calcula o Market Score V2.

    Prioriza indicadores calculados (RSI, EMAs, MACD, ATR) quando disponíveis.
    Faz fallback para cálculos baseados em candles quando indicadores são None.

    Parâmetros:
        candles:   Lista de MarketCandle em ordem cronológica (crescente).
        indicator: Último MarketIndicator calculado (opcional).
        symbol:    Identificador do ativo (para logging).
    """
    if len(candles) < MIN_CANDLES:
        logger.debug(f"[{symbol}] Dados insuficientes. Score neutro (50).")
        return ScoreDetail(
            symbol=symbol, total_score=50,
            trend_score=17.5, momentum_score=12.5,
            volume_score=12.5, volatility_score=7.5,
            candles_used=len(candles),
        )

    n = min(IDEAL_CANDLES, len(candles))
    recent  = candles[-n:]
    closes  = [float(c.close)  for c in recent]
    volumes = [float(c.volume) for c in recent]
    highs   = [float(c.high)   for c in recent]
    lows    = [float(c.low)    for c in recent]

    # ── Trend ────────────────────────────────────────────────────────────────
    if indicator and all(v is not None for v in [indicator.ema_9, indicator.ema_21, indicator.ema_50]):
        trend_score = _trend_from_emas(indicator)
    else:
        trend_score = _trend_from_sma(closes)

    # ── Momentum ─────────────────────────────────────────────────────────────
    if indicator and indicator.rsi is not None:
        momentum_score = _momentum_from_indicators(indicator)
    else:
        momentum_score = float(SCORE_WEIGHTS["momentum"]) / 2

    # ── Volume ───────────────────────────────────────────────────────────────
    volume_score = _volume_score(volumes)

    # ── Volatility ───────────────────────────────────────────────────────────
    if indicator and indicator.atr is not None and closes:
        volatility_score = _volatility_from_atr(indicator.atr, closes[-1])
    else:
        volatility_score = _volatility_from_candles(highs, lows)

    total = int(round(trend_score + momentum_score + volume_score + volatility_score))
    total = max(0, min(100, total))

    logger.debug(
        f"[{symbol}] Score={total} "
        f"(trend={trend_score:.1f} mom={momentum_score:.1f} "
        f"vol={volume_score:.1f} vlt={volatility_score:.1f})"
    )

    return ScoreDetail(
        symbol=symbol, total_score=total,
        trend_score=round(trend_score, 1),
        momentum_score=round(momentum_score, 1),
        volume_score=round(volume_score, 1),
        volatility_score=round(volatility_score, 1),
        candles_used=n,
    )


# ── Componentes de score ──────────────────────────────────────────────────────

def _trend_from_emas(ind: MarketIndicator) -> float:
    """Tendência baseada no alinhamento de EMAs (0–35)."""
    W = float(SCORE_WEIGHTS["trend"])
    e9, e21, e50, e200 = ind.ema_9, ind.ema_21, ind.ema_50, ind.ema_200

    points = 0.0
    total_criteria = 3.0 if e200 is None else 4.0

    if e9  > e21:  points += 1
    if e21 > e50:  points += 1
    if e200 is not None:
        if e50 > e200: points += 1

    # Bônus MACD
    if ind.macd is not None:
        if ind.macd > 0:
            points += 0.5
        total_criteria += 0.5

    return (points / total_criteria) * W


def _trend_from_sma(closes: list[float]) -> float:
    """Tendência baseada no desvio da SMA (fallback sem EMAs)."""
    W = float(SCORE_WEIGHTS["trend"])
    if not closes:
        return W / 2

    sma = sum(closes) / len(closes)
    if sma == 0:
        return W / 2

    deviation_pct = (closes[-1] - sma) / sma * 100
    # Mapeia [-5%, +5%] → [0, W]
    score = (W / 2) + deviation_pct * (W / 10)
    return max(0.0, min(W, score))


def _momentum_from_indicators(ind: MarketIndicator) -> float:
    """Momentum baseado em RSI + MACD (0–25)."""
    W   = float(SCORE_WEIGHTS["momentum"])
    rsi = ind.rsi

    # RSI: 50 = neutro (W/2), 70 = máximo bônus, <30 = mínimo
    # Mapeia RSI [20, 80] → [0, W] com pico em 65
    if rsi <= 20:
        rsi_score = 0.0
    elif rsi >= 80:
        rsi_score = W * 0.4   # overbought: penaliza
    else:
        # Curva: máximo em RSI=65
        rsi_score = W * (1 - abs(rsi - 65) / 45)
        rsi_score = max(0.0, rsi_score)

    # MACD: bônus +20% se positivo, bônus adicional se histogram positivo
    macd_bonus = 0.0
    if ind.macd is not None and ind.macd > 0:
        macd_bonus += 0.15
    if ind.macd_histogram is not None and ind.macd_histogram > 0:
        macd_bonus += 0.15

    score = rsi_score * (1.0 + macd_bonus)
    return max(0.0, min(W, score))


def _volume_score(volumes: list[float]) -> float:
    """Volume atual vs. média histórica (0–25)."""
    W = float(SCORE_WEIGHTS["volume"])
    if len(volumes) < 2:
        return W / 2

    avg = sum(volumes[:-1]) / len(volumes[:-1])
    if avg == 0:
        return W / 2

    ratio = volumes[-1] / avg
    # Mapeia [0.5×, 2.5×] → [0, W]
    score = (ratio - 0.5) / 2.0 * W
    return max(0.0, min(W, score))


def _volatility_from_atr(atr: float, price: float) -> float:
    """Volatilidade baseada em ATR% (0–15). Faixa ideal: 1–2.5%."""
    W = float(SCORE_WEIGHTS["volatility"])
    if price <= 0:
        return W / 2

    atr_pct = (atr / price) * 100
    # Pico em 1.75%, penaliza desvios
    score = W - abs(atr_pct - 1.75) * 4.0
    return max(0.0, min(W, score))


def _volatility_from_candles(highs: list[float], lows: list[float]) -> float:
    """Volatilidade baseada no range médio dos candles (fallback)."""
    W = float(SCORE_WEIGHTS["volatility"])
    if not highs or not lows:
        return W / 2

    ranges = [
        (h - l) / l * 100
        for h, l in zip(highs, lows)
        if l > 0
    ]
    if not ranges:
        return W / 2

    avg_range = sum(ranges) / len(ranges)
    score = W - abs(avg_range - 2.0) * 4.0
    return max(0.0, min(W, score))
