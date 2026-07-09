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
    atr_1m_pct: float | None = None  # V7: ATR(14) percentual para SL adaptativo
    obv_trend:  str | None = None    # V7: OBV BULL/BEAR/NEUTRAL (confirma volume)
    volume_spike: bool = False       # V7: spike de volume na última vela 5m
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


def _volumes(candles) -> list[float]:
    return [float(c.volume) for c in candles]

def _obv(candles) -> list[float]:
    """On-Balance Volume: OBV acumula volume com base no fechamento."""
    obv_vals = [0.0]
    for i in range(1, len(candles)):
        close  = float(candles[i].close)
        pclose = float(candles[i - 1].close)
        vol    = float(candles[i].volume)
        if close > pclose:
            obv_vals.append(obv_vals[-1] + vol)
        elif close < pclose:
            obv_vals.append(obv_vals[-1] - vol)
        else:
            obv_vals.append(obv_vals[-1])
    return obv_vals

def _obv_trend(obv_vals: list[float], period: int = 14) -> str:
    """OBV_EMA(period) vs OBV_EMA(period*2): 'BULL' | 'BEAR' | 'NEUTRAL'."""
    if len(obv_vals) < period * 2:
        return "NEUTRAL"
    fast = _ema(obv_vals, period)
    slow = _ema(obv_vals, period * 2)
    margin = (fast - slow) / abs(slow) * 100 if slow != 0 else 0
    if margin > 0.5:
        return "BULL"
    if margin < -0.5:
        return "BEAR"
    return "NEUTRAL"

def _volume_spike(candles, lookback: int = 20, multiplier: float = 1.5) -> bool:
    """Volume do último candle > multiplier × média dos últimos lookback."""
    if len(candles) < lookback + 1:
        return False
    vols = _volumes(candles)
    avg  = sum(vols[-(lookback+1):-1]) / lookback
    return vols[-1] > avg * multiplier


def _atr(candles, period: int = 14) -> float:
    """
    Calcula ATR (Average True Range) a partir de velas OHLCV.
    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    ATR = EMA(TR, period)
    """
    if len(candles) < period + 1:
        return 0.0
    tr_values = []
    prev_close = float(candles[0].close)
    for c in candles[1:]:
        high = float(c.high)
        low  = float(c.low)
        tr   = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_values.append(tr)
        prev_close = float(c.close)
    # ATR = EMA do TR (Wilder's smoothing)
    atr = sum(tr_values[:period]) / period
    k = 1.0 / period
    for tr in tr_values[period:]:
        atr = tr * k + atr * (1 - k)
    return atr


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


def _confirm_5m(candles_5m, trend: str) -> tuple[bool, float | None, str | None, bool, list[str]]:
    """
    Confirma no 5m com OBV (V7).
    LONG : RSI 30-58, EMA9>EMA21, preço perto ou abaixo do EMA9 (pullback)
    SHORT: RSI 42-70, EMA9<EMA21, preço perto ou acima do EMA9 (bounce)
    OBV confirma direção do volume.
    Retorna: (confirm, rsi, obv_trend, volume_spike, reasons)
    """
    if len(candles_5m) < 25:
        return False, None, None, False, ["5m: candles insuficientes"]

    closes = _closes(candles_5m)
    price  = closes[-1]
    rsi    = _rsi(closes[-20:])
    ema9   = _ema(closes, 9)
    ema21  = _ema(closes, 21)

    # V7: OBV
    obv_vals     = _obv(candles_5m)
    obv_t        = _obv_trend(obv_vals, 14)
    vol_spike    = _volume_spike(candles_5m, 20, 1.5)
    reasons: list[str] = []

    if trend == "BULL":
        near_ema9 = abs(price - ema9) / ema9 <= 0.005   # dentro de 0.5%
        micro_bull = ema9 > ema21
        rsi_ok     = 30 <= rsi <= 58
        ok = micro_bull and rsi_ok and (near_ema9 or price < ema9 * 1.001)
        # OBV confirma: BULL + volume_spike recebe bonus, BEAR não invalida
        obv_ok = obv_t in ("BULL", "NEUTRAL")
        if not obv_ok:
            ok = False
        reasons.append(
            f"5m LONG: RSI={rsi:.1f} EMA9={ema9:.4f} EMA21={ema21:.4f} "
            f"near_ema9={near_ema9} micro_bull={micro_bull} ok={ok} "
            f"OBV={obv_t} spike={vol_spike}"
        )
        return ok, rsi, obv_t, vol_spike, reasons

    if trend == "BEAR":
        near_ema9  = abs(price - ema9) / ema9 <= 0.005
        micro_bear = ema9 < ema21
        rsi_ok     = 42 <= rsi <= 70
        ok = micro_bear and rsi_ok and (near_ema9 or price > ema9 * 0.999)
        # OBV confirma: BEAR + volume_spike recebe bonus
        obv_ok = obv_t in ("BEAR", "NEUTRAL")
        if not obv_ok:
            ok = False
        reasons.append(
            f"5m SHORT: RSI={rsi:.1f} EMA9={ema9:.4f} EMA21={ema21:.4f} "
            f"near_ema9={near_ema9} micro_bear={micro_bear} ok={ok} "
            f"OBV={obv_t} spike={vol_spike}"
        )
        return ok, rsi, obv_t, vol_spike, reasons

    return False, rsi, obv_t, vol_spike, [f"5m: sem confirmação para SIDEWAYS"]


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

    # V7: _confirm_5m agora retorna OBV também
    confirm, rsi_5m, obv_t, vol_spike, r5  = _confirm_5m(candles_5m, trend)
    entry,   rsi_1m, r1                     = _entry_1m(candles_1m,   trend)
    conf   = _confidence(trend, confirm, entry, rsi_5m, rsi_1m)

    # V7: ATR percentual para SL adaptativo
    atr_val  = _atr(candles_1m, 14)
    atr_pct  = round((atr_val / price * 100), 4) if atr_val > 0 and price > 0 else None

    # V7: OBV boost na confidence se volume confirma direção
    if confirm and obv_t == trend and vol_spike:
        conf = min(conf + 5, 100)
    # V7: OBV penaliza se volume contradiz direção
    if confirm and obv_t is not None and obv_t not in (trend, "NEUTRAL"):
        conf = max(conf - 10, 0)

    direction: Direction = ("LONG" if trend == "BULL" else "SHORT") if (confirm and entry) else "NONE"

    return ScalperSignalResult(
        symbol       = symbol,
        direction    = direction,
        price        = price,
        confidence   = conf,
        trend_15m    = trend,
        confirm_5m   = confirm,
        entry_1m     = entry,
        rsi_1m       = rsi_1m,
        rsi_5m       = rsi_5m,
        ema9_15m     = ema9_15m,
        ema21_15m    = ema21_15m,
        atr_1m_pct   = atr_pct,
        obv_trend    = obv_t,
        volume_spike = vol_spike,
        reasons      = r15 + r5 + r1,
    )
