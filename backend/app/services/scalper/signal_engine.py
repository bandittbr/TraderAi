"""
Scalper Signal Engine — Multi-Timeframe (Fase 13)
Lógica: 15m (tendência) → 5m (confirmação) → 1m (entrada)
Completamente independente do Signal Engine do Paper Trading.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal

# ─ Tipos ─────────────────────────────────────────────────────────────────────
Direction = Literal["LONG", "SHORT", "NONE"]

SCALPER_SYMBOLS   = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT"]
SCALPER_TIMEFRAMES = ["1m", "5m", "15m"]


@dataclass
class ScalperSignalResult:
    symbol:     str
    direction:  Direction
    price:      float
    confidence: float          # 0-100
    trend_15m:  str            # BULL / BEAR / SIDEWAYS
    confirm_5m: bool
    entry_1m:   bool
    rsi_1m:     float | None = None
    rsi_5m:     float | None = None
    ema9_15m:   float | None = None
    ema21_15m:  float | None = None
    reasons:    list[str]    = field(default_factory=list)


# ─ Helpers de indicadores inline ──────────────────────────────────────────────
def _closes(candles) -> list[float]:
    return [float(c.close) for c in candles]

def _highs(candles) -> list[float]:
    return [float(c.high) for c in candles]

def _lows(candles) -> list[float]:
    return [float(c.low) for c in candles]

def _ema(values: list[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0.0
    k   = 2.0 / (period + 1)
    val = sum(values[:period]) / period
    for v in values[period:]:
        val = v * k + val * (1 - k)
    return val

def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    diffs  = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains  = [max(d, 0.0) for d in diffs]
    losses = [max(-d, 0.0) for d in diffs]
    ag     = sum(gains[-period:])  / period
    al     = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return round(100 - (100 / (1 + rs)), 2)

def _macd_histogram(closes: list[float]) -> float:
    """Diferença MACD-line menos signal (9-EMA do MACD)."""
    if len(closes) < 35:
        return 0.0
    ema12_vals, ema26_vals = [], []
    k12, k26 = 2/13, 2/27
    e12 = e26 = closes[0]
    for c in closes:
        e12 = c * k12 + e12 * (1 - k12)
        e26 = c * k26 + e26 * (1 - k26)
        ema12_vals.append(e12)
        ema26_vals.append(e26)
    macd_line = [ema12_vals[i] - ema26_vals[i] for i in range(len(closes))]
    k9  = 2/10
    sig = macd_line[0]
    for m in macd_line:
        sig = m * k9 + sig * (1 - k9)
    return round(macd_line[-1] - sig, 8)


# ─ Etapas MTF ─────────────────────────────────────────────────────────────────
def _trend_15m(candles_15m) -> tuple[str, float | None, float | None, float | None, list[str]]:
    """
    Determina tendência no 15m.
    BULL  : EMA9 > EMA21 > EMA50 e preço > EMA21
    BEAR  : EMA9 < EMA21 < EMA50 e preço < EMA21
    SIDEWAYS: caso contrário
    """
    if len(candles_15m) < 55:
        return "SIDEWAYS", None, None, None, ["15m: candles insuficientes"]

    closes = _closes(candles_15m)
    price  = closes[-1]
    ema9   = _ema(closes, 9)
    ema21  = _ema(closes, 21)
    ema50  = _ema(closes, 50)
    reasons: list[str] = []

    if ema9 > ema21 > ema50 and price > ema21:
        margin = round((ema9 - ema21) / ema21 * 100, 3)
        reasons.append(f"15m BULL: EMA9>{ema9:.2f} EMA21>{ema21:.2f} EMA50>{ema50:.2f} spread={margin}%")
        return "BULL", ema9, ema21, ema50, reasons

    if ema9 < ema21 < ema50 and price < ema21:
        margin = round((ema21 - ema9) / ema21 * 100, 3)
        reasons.append(f"15m BEAR: EMA9<{ema9:.2f} EMA21<{ema21:.2f} EMA50<{ema50:.2f} spread={margin}%")
        return "BEAR", ema9, ema21, ema50, reasons

    reasons.append(f"15m SIDEWAYS: EMA9={ema9:.2f} EMA21={ema21:.2f} EMA50={ema50:.2f}")
    return "SIDEWAYS", ema9, ema21, ema50, reasons


def _confirm_5m(candles_5m, trend: str) -> tuple[bool, float | None, list[str]]:
    """
    Confirma no 5m.
    LONG : RSI 30-58, EMA9>EMA21, preço perto ou abaixo do EMA9 (pullback)
    SHORT: RSI 42-70, EMA9<EMA21, preço perto ou acima do EMA9 (bounce)
    """
    if len(candles_5m) < 25:
        return False, None, ["5m: candles insuficientes"]

    closes = _closes(candles_5m)
    price  = closes[-1]
    rsi    = _rsi(closes[-20:])
    ema9   = _ema(closes, 9)
    ema21  = _ema(closes, 21)
    reasons: list[str] = []

    if trend == "BULL":
        near_ema9 = abs(price - ema9) / ema9 <= 0.005   # dentro de 0.5%
        micro_bull = ema9 > ema21
        rsi_ok     = 30 <= rsi <= 58
        ok = micro_bull and rsi_ok and (near_ema9 or price < ema9 * 1.001)
        reasons.append(
            f"5m LONG confirm: RSI={rsi:.1f} EMA9={ema9:.4f} EMA21={ema21:.4f} "
            f"near_ema9={near_ema9} micro_bull={micro_bull} ok={ok}"
        )
        return ok, rsi, reasons

    if trend == "BEAR":
        near_ema9  = abs(price - ema9) / ema9 <= 0.005
        micro_bear = ema9 < ema21
        rsi_ok     = 42 <= rsi <= 70
        ok = micro_bear and rsi_ok and (near_ema9 or price > ema9 * 0.999)
        reasons.append(
            f"5m SHORT confirm: RSI={rsi:.1f} EMA9={ema9:.4f} EMA21={ema21:.4f} "
            f"near_ema9={near_ema9} micro_bear={micro_bear} ok={ok}"
        )
        return ok, rsi, reasons

    return False, rsi, [f"5m: sem confirmação para SIDEWAYS"]


def _entry_1m(candles_1m, trend: str) -> tuple[bool, float | None, list[str]]:
    """
    Gatilho de entrada no 1m.
    LONG : último candle bullish + MACD histogram cruzou acima de zero
    SHORT: último candle bearish + MACD histogram cruzou abaixo de zero
    """
    if len(candles_1m) < 36:
        return False, None, ["1m: candles insuficientes"]

    closes = _closes(candles_1m)
    rsi    = _rsi(closes[-20:])
    hist   = _macd_histogram(closes)
    last   = candles_1m[-1]
    prev   = candles_1m[-2]
    reasons: list[str] = []

    last_bullish = float(last.close) > float(last.open)
    last_bearish = float(last.close) < float(last.open)
    prev_hist    = _macd_histogram(closes[:-1]) if len(closes) > 36 else 0.0

    if trend == "BULL":
        macd_cross = prev_hist < 0 <= hist or hist > 0
        rsi_ok     = 35 <= rsi <= 70
        ok = last_bullish and macd_cross and rsi_ok
        reasons.append(
            f"1m LONG entry: bullish={last_bullish} MACD_hist={hist:.6f} "
            f"cross={macd_cross} RSI={rsi:.1f} ok={ok}"
        )
        return ok, rsi, reasons

    if trend == "BEAR":
        macd_cross = prev_hist > 0 >= hist or hist < 0
        rsi_ok     = 30 <= rsi <= 65
        ok = last_bearish and macd_cross and rsi_ok
        reasons.append(
            f"1m SHORT entry: bearish={last_bearish} MACD_hist={hist:.6f} "
            f"cross={macd_cross} RSI={rsi:.1f} ok={ok}"
        )
        return ok, rsi, reasons

    return False, rsi, ["1m: SIDEWAYS — sem entrada"]


def _confidence(
    trend: str, confirm: bool, entry: bool,
    rsi_5m: float | None, rsi_1m: float | None,
) -> float:
    """Score 0-100 baseado na qualidade dos filtros."""
    base = 65.0
    if not confirm or not entry:
        return 0.0
    # Bonus por RSI ideal
    if rsi_5m is not None:
        ideal_5m = (38 <= rsi_5m <= 52) if trend == "BULL" else (48 <= rsi_5m <= 62)
        if ideal_5m:
            base += 10.0
    if rsi_1m is not None:
        ideal_1m = (40 <= rsi_1m <= 60)
        if ideal_1m:
            base += 10.0
    return min(base, 100.0)


# ─ Função principal ───────────────────────────────────────────────────────────
def evaluate_scalper_signal(
    symbol: str,
    candles_15m: list,
    candles_5m:  list,
    candles_1m:  list,
) -> ScalperSignalResult:
    """
    Avalia sinal MTF completo para um símbolo.
    Retorna ScalperSignalResult com direction=NONE se nenhum filtro passar.
    """
    price = float(candles_1m[-1].close) if candles_1m else 0.0

    trend, ema9_15m, ema21_15m, _, r15 = _trend_15m(candles_15m)

    if trend == "SIDEWAYS":
        return ScalperSignalResult(
            symbol=symbol, direction="NONE", price=price,
            confidence=0.0, trend_15m=trend, confirm_5m=False, entry_1m=False,
            reasons=r15,
        )

    confirm, rsi_5m, r5  = _confirm_5m(candles_5m, trend)
    entry,   rsi_1m, r1  = _entry_1m(candles_1m,   trend)
    conf   = _confidence(trend, confirm, entry, rsi_5m, rsi_1m)

    direction: Direction = ("LONG" if trend == "BULL" else "SHORT") if (confirm and entry) else "NONE"

    return ScalperSignalResult(
        symbol     = symbol,
        direction  = direction,
        price      = price,
        confidence = conf,
        trend_15m  = trend,
        confirm_5m = confirm,
        entry_1m   = entry,
        rsi_1m     = rsi_1m,
        rsi_5m     = rsi_5m,
        ema9_15m   = ema9_15m,
        ema21_15m  = ema21_15m,
        reasons    = r15 + r5 + r1,
    )
