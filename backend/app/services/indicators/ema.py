"""
EMA — Exponential Moving Average.

Algoritmo:
  1. Semente = SMA dos primeiros `period` candles.
  2. Para cada candle seguinte: EMA = price * k + prev_EMA * (1-k)
     onde k = 2 / (period + 1)  (fator de suavização padrão).

Retorna apenas o valor mais recente (ponto final da série).
"""


def _ema_series(closes: list[float], period: int) -> list[float]:
    """
    Retorna a série completa de valores EMA.
    O primeiro valor é o SMA dos `period` primeiros closes.
    O comprimento da lista resultante é len(closes) - period + 1.
    """
    if len(closes) < period:
        return []

    k = 2.0 / (period + 1)
    ema = sum(closes[:period]) / period
    result = [ema]

    for price in closes[period:]:
        ema = price * k + ema * (1.0 - k)
        result.append(ema)

    return result


def calculate_ema(closes: list[float], period: int) -> float | None:
    """
    Calcula o valor atual (mais recente) da EMA.

    Parâmetros:
        closes: Lista de fechamentos em ordem cronológica.
        period: Período da EMA (ex: 9, 21, 50, 200).

    Retorna:
        Último valor da EMA ou None se dados insuficientes.
    """
    series = _ema_series(closes, period)
    return round(series[-1], 8) if series else None
