"""
RSI — Relative Strength Index (Wilder, 14 períodos).

Algoritmo:
  1. Calcula as variações (close[i] - close[i-1]).
  2. Separa gains (variações positivas) e losses (abs das negativas).
  3. Média inicial (SMA) para o primeiro período.
  4. Suavização de Wilder: avg = (prev_avg * (period-1) + current) / period.
  5. RS = avg_gain / avg_loss; RSI = 100 - 100/(1+RS).

Exige no mínimo period+1 candles (15 para RSI-14).
"""


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    """
    Calcula o RSI usando suavização de Wilder (SMMA).

    Parâmetros:
        closes: Lista de preços de fechamento em ordem cronológica.
        period: Número de períodos (padrão 14).

    Retorna:
        Valor RSI (0–100) ou None se dados insuficientes.
    """
    if len(closes) < period + 1:
        return None

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains   = [max(c, 0.0) for c in changes]
    losses  = [abs(min(c, 0.0)) for c in changes]

    # Semente: SMA do primeiro período
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Suavização de Wilder para os períodos restantes
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0.0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 4)
