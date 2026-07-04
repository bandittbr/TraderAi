"""
ATR — Average True Range (Wilder, 14 períodos).

True Range para cada candle:
  TR = max(high - low, |high - prev_close|, |low - prev_close|)

ATR = Suavização de Wilder do TR ao longo de `period` períodos.
Exige no mínimo period + 1 candles (15 para ATR-14).
"""


def calculate_atr(
    highs:  list[float],
    lows:   list[float],
    closes: list[float],
    period: int = 14,
) -> float | None:
    """
    Calcula o ATR usando suavização de Wilder (SMMA).

    Parâmetros:
        highs:  Lista de máximas em ordem cronológica.
        lows:   Lista de mínimas.
        closes: Lista de fechamentos.
        period: Número de períodos (padrão 14).

    Retorna:
        Valor ATR ou None se dados insuficientes.
    """
    n = len(closes)
    if n < period + 1 or len(highs) != n or len(lows) != n:
        return None

    tr_values: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i]  - closes[i - 1]),
        )
        tr_values.append(tr)

    if len(tr_values) < period:
        return None

    # Semente: SMA dos primeiros `period` TR
    atr = sum(tr_values[:period]) / period

    # Suavização de Wilder
    for tr in tr_values[period:]:
        atr = (atr * (period - 1) + tr) / period

    return round(atr, 8)
