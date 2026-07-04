"""
Liquidity Sweep Detector — Phase 7 (Smart Money Concepts)

Detecta eventos onde o preço "varre" liquidez acumulada além de swing points
e depois reverte — padrão clássico de movimentação institucional.

Tipos detectados:
  BUY_SIDE_SWEEP  — preço perfura acima de swing high e reverte para baixo
  SELL_SIDE_SWEEP — preço perfura abaixo de swing low e reverte para cima
  STOP_HUNT       — sweep rápido + reversão forte (magnitude > 2x tolerance)
  FALSE_BREAKOUT  — fechamento além do swing mas sem follow-through
  FALSE_BREAKDOWN — espelho do false breakout para baixo

Regras matemáticas puras — sem IA, sem ML.

Parâmetros padrão:
  sweep_tolerance  = 0.001  (0.1% acima/abaixo do swing)
  reversal_pct     = 0.003  (0.3% de reversão mínima para confirmar sweep)
  lookback_candles = 10     (quantos candles usar para referenciar swing)
  stop_hunt_mult   = 2.0    (multiplicador para distinguir stop hunt de sweep simples)
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional


# ── Tipos de sweep ─────────────────────────────────────────────────────────────

class SweepType(str, enum.Enum):
    BUY_SIDE_SWEEP  = "BUY_SIDE_SWEEP"
    SELL_SIDE_SWEEP = "SELL_SIDE_SWEEP"
    STOP_HUNT       = "STOP_HUNT"
    FALSE_BREAKOUT  = "FALSE_BREAKOUT"
    FALSE_BREAKDOWN = "FALSE_BREAKDOWN"


class SweepStrength(str, enum.Enum):
    WEAK     = "WEAK"
    MODERATE = "MODERATE"
    STRONG   = "STRONG"


# ── Resultado ──────────────────────────────────────────────────────────────────

@dataclass
class SweepEvent:
    sweep_type:  SweepType
    strength:    SweepStrength
    price:       float          # preço do wick que varreu a liquidez
    swept_level: float          # nível de swing varrido
    close:       float          # fechamento do candle
    timestamp:   int            # epoch seconds
    candle_index: int           # índice no array de candles
    penetration_pct: float      # % de penetração além do swing
    reversal_pct:    float      # % de reversão em relação ao wick
    is_stop_hunt:    bool = False
    reasons: List[str] = field(default_factory=list)


@dataclass
class SweepAnalysis:
    """Resultado completo da análise de sweeps para uma série de candles."""
    events:           List[SweepEvent]
    buy_side_sweeps:  List[SweepEvent]   # eventos bull → institucional comprando
    sell_side_sweeps: List[SweepEvent]   # eventos bear → institucional vendendo
    last_sweep:       Optional[SweepEvent] = None
    recent_buy_sweep: Optional[SweepEvent] = None
    recent_sell_sweep: Optional[SweepEvent] = None
    # Para Signal Engine V5
    has_recent_buy_sweep:  bool = False
    has_recent_sell_sweep: bool = False
    sweep_bias: str = "NEUTRAL"   # BULLISH | BEARISH | NEUTRAL


# ── Funções auxiliares ─────────────────────────────────────────────────────────

def _classify_strength(penetration_pct: float, sweep_tolerance: float) -> SweepStrength:
    """Classifica a força do sweep com base na penetração relativa ao tolerance."""
    ratio = penetration_pct / sweep_tolerance if sweep_tolerance > 0 else 1.0
    if ratio >= 3.0:
        return SweepStrength.STRONG
    if ratio >= 1.5:
        return SweepStrength.MODERATE
    return SweepStrength.WEAK


def _rolling_high(candles, end_idx: int, lookback: int) -> float:
    """Máxima dos últimos `lookback` candles terminando em end_idx (exclusive)."""
    start = max(0, end_idx - lookback)
    return max(c.high for c in candles[start:end_idx])


def _rolling_low(candles, end_idx: int, lookback: int) -> float:
    """Mínima dos últimos `lookback` candles terminando em end_idx (exclusive)."""
    start = max(0, end_idx - lookback)
    return min(c.low for c in candles[start:end_idx])


# ── Detector principal ─────────────────────────────────────────────────────────

def detect_sweeps(
    candles,
    sweep_tolerance: float  = 0.001,
    reversal_pct:    float  = 0.003,
    lookback_candles: int   = 10,
    stop_hunt_mult:  float  = 2.0,
    recent_window:   int    = 5,
) -> SweepAnalysis:
    """
    Detecta eventos de liquidity sweep em uma série de candles.

    Args:
        candles:          Lista de candles (precisam ter high, low, close, timestamp).
        sweep_tolerance:  % mínimo de penetração além do swing para qualificar sweep.
        reversal_pct:     % mínimo de reversão do wick para confirmar sweep.
        lookback_candles: Janela de lookback para determinar o swing de referência.
        stop_hunt_mult:   Multiplicador de penetração para classificar como Stop Hunt.
        recent_window:    Quantos candles recentes considerar para has_recent_*.

    Returns:
        SweepAnalysis com todos os eventos classificados.
    """
    n = len(candles)
    if n < lookback_candles + 1:
        return SweepAnalysis(
            events=[], buy_side_sweeps=[], sell_side_sweeps=[],
            sweep_bias="NEUTRAL",
        )

    events: List[SweepEvent] = []

    for i in range(lookback_candles, n):
        c = candles[i]

        # Swing de referência (sem incluir o candle atual)
        ref_high = _rolling_high(candles, i, lookback_candles)
        ref_low  = _rolling_low(candles,  i, lookback_candles)

        candle_range = c.high - c.low
        if candle_range <= 0:
            continue

        # ── BUY SIDE SWEEP (acima da high de referência) ─────────────────────
        if c.high > ref_high * (1.0 + sweep_tolerance):
            penetration = (c.high - ref_high) / ref_high
            reversal    = (c.high - c.close) / candle_range  # quanto do wick virou

            if reversal >= reversal_pct / sweep_tolerance * 0.1:  # normalizado
                is_stop_hunt = penetration >= sweep_tolerance * stop_hunt_mult
                reasons = [
                    f"Wick acima de ref_high {ref_high:.2f} (+{penetration*100:.3f}%)",
                    f"Reversão {(c.high-c.close)/c.high*100:.3f}%",
                ]
                if is_stop_hunt:
                    sweep_t = SweepType.STOP_HUNT
                    reasons.append("Penetração ≥ 2× tolerance → Stop Hunt")
                elif c.close > ref_high:
                    sweep_t = SweepType.FALSE_BREAKOUT
                    reasons.append("Fechamento acima do swing → False Breakout")
                else:
                    sweep_t = SweepType.BUY_SIDE_SWEEP
                    reasons.append("Fechamento abaixo do swing → Buy Side Sweep confirmado")

                events.append(SweepEvent(
                    sweep_type       = sweep_t,
                    strength         = _classify_strength(penetration, sweep_tolerance),
                    price            = c.high,
                    swept_level      = ref_high,
                    close            = c.close,
                    timestamp        = getattr(c, "timestamp", i),
                    candle_index     = i,
                    penetration_pct  = penetration * 100,
                    reversal_pct     = (c.high - c.close) / c.high * 100,
                    is_stop_hunt     = is_stop_hunt,
                    reasons          = reasons,
                ))

        # ── SELL SIDE SWEEP (abaixo da low de referência) ────────────────────
        if c.low < ref_low * (1.0 - sweep_tolerance):
            penetration = (ref_low - c.low) / ref_low
            reversal    = (c.close - c.low) / candle_range

            if reversal >= reversal_pct / sweep_tolerance * 0.1:
                is_stop_hunt = penetration >= sweep_tolerance * stop_hunt_mult
                reasons = [
                    f"Wick abaixo de ref_low {ref_low:.2f} (-{penetration*100:.3f}%)",
                    f"Reversão {(c.close-c.low)/c.low*100:.3f}%",
                ]
                if is_stop_hunt:
                    sweep_t = SweepType.STOP_HUNT
                    reasons.append("Penetração ≥ 2× tolerance → Stop Hunt")
                elif c.close < ref_low:
                    sweep_t = SweepType.FALSE_BREAKDOWN
                    reasons.append("Fechamento abaixo do swing → False Breakdown")
                else:
                    sweep_t = SweepType.SELL_SIDE_SWEEP
                    reasons.append("Fechamento acima do swing → Sell Side Sweep confirmado")

                events.append(SweepEvent(
                    sweep_type       = sweep_t,
                    strength         = _classify_strength(penetration, sweep_tolerance),
                    price            = c.low,
                    swept_level      = ref_low,
                    close            = c.close,
                    timestamp        = getattr(c, "timestamp", i),
                    candle_index     = i,
                    penetration_pct  = penetration * 100,
                    reversal_pct     = (c.close - c.low) / ref_low * 100,
                    is_stop_hunt     = is_stop_hunt,
                    reasons          = reasons,
                ))

    # ── Classificar em buy/sell ────────────────────────────────────────────────
    buy_events  = [e for e in events if e.sweep_type in (
        SweepType.BUY_SIDE_SWEEP, SweepType.STOP_HUNT
    )]
    sell_events = [e for e in events if e.sweep_type in (
        SweepType.SELL_SIDE_SWEEP, SweepType.STOP_HUNT
    )]
    # False breakout/breakdown também qualificam
    buy_events  += [e for e in events if e.sweep_type == SweepType.FALSE_BREAKOUT]
    sell_events += [e for e in events if e.sweep_type == SweepType.FALSE_BREAKDOWN]

    # Recentes (últimos `recent_window` candles)
    min_recent_idx = n - recent_window - 1
    recent_buy  = [e for e in buy_events  if e.candle_index >= min_recent_idx]
    recent_sell = [e for e in sell_events if e.candle_index >= min_recent_idx]

    last_buy  = recent_buy[-1]  if recent_buy  else None
    last_sell = recent_sell[-1] if recent_sell else None
    last_any  = events[-1]      if events       else None

    # Bias: qual o sweep mais recente
    bias = "NEUTRAL"
    if last_buy and last_sell:
        bias = "BULLISH" if last_buy.candle_index > last_sell.candle_index else "BEARISH"
    elif last_buy:
        bias = "BULLISH"
    elif last_sell:
        bias = "BEARISH"

    return SweepAnalysis(
        events            = events,
        buy_side_sweeps   = buy_events,
        sell_side_sweeps  = sell_events,
        last_sweep        = last_any,
        recent_buy_sweep  = last_buy,
        recent_sell_sweep = last_sell,
        has_recent_buy_sweep  = len(recent_buy)  > 0,
        has_recent_sell_sweep = len(recent_sell) > 0,
        sweep_bias        = bias,
    )
