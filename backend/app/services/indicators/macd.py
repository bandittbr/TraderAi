"""
MACD — Moving Average Convergence Divergence.

Componentes:
  • MACD Line    = EMA(12) - EMA(26)
  • Signal Line  = EMA(9) da MACD Line
  • Histogram    = MACD Line - Signal Line

Mínimo de candles necessário:
  26 (para EMA26) + 9 - 1 (para Signal) = 34 candles.
"""

from app.services.indicators.ema import _ema_series


def calculate_macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float | None, float | None, float | None]:
    """
    Calcula MACD Line, Signal Line e Histogram.

    Parâmetros:
        closes: Lista de fechamentos em ordem cronológica.
        fast:   Período da EMA rápida (padrão 12).
        slow:   Período da EMA lenta (padrão 26).
        signal: Período da Signal Line (padrão 9).

    Retorna:
        (macd, signal_line, histogram) — qualquer um pode ser None
        se não houver dados suficientes.
    """
    ema_fast = _ema_series(closes, fast)   # len = len(closes) - fast + 1
    ema_slow = _ema_series(closes, slow)   # len = len(closes) - slow + 1

    if not ema_fast or not ema_slow:
        return None, None, None

    # Alinha as séries: ema_fast é `slow - fast` elementos mais longa
    offset = len(ema_fast) - len(ema_slow)
    macd_series = [
        ema_fast[i + offset] - ema_slow[i]
        for i in range(len(ema_slow))
    ]

    if not macd_series:
        return None, None, None

    macd_val = macd_series[-1]

    # Signal Line: EMA(signal) da série MACD
    signal_series = _ema_series(macd_series, signal)
    if not signal_series:
        return round(macd_val, 8), None, None

    signal_val    = signal_series[-1]
    histogram_val = macd_val - signal_val

    return round(macd_val, 8), round(signal_val, 8), round(histogram_val, 8)
