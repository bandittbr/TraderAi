"""
Swing Detector — Phase 6.5

Detecta topos (Swing High) e fundos (Swing Low) nos candles de forma determinística.

Algoritmo:
  Um candle i é Swing High se: high[i] >= high[j] para todo j em [i-N, i+N]
  Um candle i é Swing Low  se: low[i]  <= low[j]  para todo j em [i-N, i+N]

  N = swing_length (padrão: 5) — controla sensibilidade:
    N menor → mais swings detectados (mais ruído)
    N maior → menos swings (estrutura macro)

Tudo determinístico: mesma entrada → mesma saída.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SWING_LENGTH_DEFAULT = 5   # candles de cada lado para confirmar pivô


@dataclass(frozen=True)
class SwingPoint:
    """Representa um topo ou fundo identificado nos candles."""
    index:     int              # posição na lista de candles
    price:     float            # high (para SH) ou low (para SL)
    timestamp: int              # epoch seconds
    kind:      Literal["HIGH", "LOW"]

    def __repr__(self) -> str:
        return f"<SwingPoint {self.kind} {self.price:.2f} @ idx={self.index}>"


def detect_swings(
    candles,                             # list[MarketCandle]
    swing_length: int = SWING_LENGTH_DEFAULT,
) -> list[SwingPoint]:
    """
    Detecta todos os Swing Highs e Swing Lows nos candles.

    Args:
        candles:      lista de MarketCandle em ordem cronológica (antigo→novo)
        swing_length: nº de candles de cada lado para confirmar o pivô

    Returns:
        Lista de SwingPoint ordenada por index (tempo).
        Swing Highs e Swing Lows intercalados em ordem cronológica.
    """
    n = len(candles)
    if n < swing_length * 2 + 1:
        return []

    swings: list[SwingPoint] = []

    for i in range(swing_length, n - swing_length):
        hi = candles[i].high
        lo = candles[i].low

        # Verifica Swing High: high[i] deve ser >= todos os N vizinhos
        is_sh = all(
            hi >= candles[j].high
            for j in range(i - swing_length, i + swing_length + 1)
            if j != i
        )
        # Verifica Swing Low: low[i] deve ser <= todos os N vizinhos
        is_sl = all(
            lo <= candles[j].low
            for j in range(i - swing_length, i + swing_length + 1)
            if j != i
        )

        if is_sh:
            swings.append(SwingPoint(
                index=i, price=hi,
                timestamp=candles[i].timestamp, kind="HIGH",
            ))
        if is_sl:
            swings.append(SwingPoint(
                index=i, price=lo,
                timestamp=candles[i].timestamp, kind="LOW",
            ))

    # Ordena por index (cronológico)
    swings.sort(key=lambda s: (s.index, s.kind))
    return swings


def get_recent_swings(
    candles,
    swing_length: int = SWING_LENGTH_DEFAULT,
    max_swings: int = 20,
) -> tuple[list[SwingPoint], list[SwingPoint]]:
    """
    Retorna as últimas max_swings ocorrências de SH e SL separadamente.
    Útil para análise de estrutura sem processar toda a série.

    Returns:
        (swing_highs, swing_lows) — cada lista ordenada do mais antigo ao mais novo
    """
    all_swings = detect_swings(candles, swing_length)
    highs = [s for s in all_swings if s.kind == "HIGH"][-max_swings:]
    lows  = [s for s in all_swings if s.kind == "LOW"][-max_swings:]
    return highs, lows
