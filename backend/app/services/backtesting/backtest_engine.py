"""
TradeAI - Backtest Engine V2 (Futures: LONG + SHORT)

Estrategia testada:
  LONG:  BUY  + confidence >= 70  -> abrir LONG
  SHORT: SELL + confidence >= 70  -> abrir SHORT

Fechamento:
  LONG:  SL preco <= entry*(1-SL%), TP preco >= entry*(1+TP%), ou sinal SELL
  SHORT: SL preco >= entry*(1+SL%), TP preco <= entry*(1-TP%), ou sinal BUY

PnL:
  LONG  = risk_per_trade * ((exit - entry) / entry)
  SHORT = risk_per_trade * ((entry - exit) / entry)

Metricas separadas por LONG/SHORT para analise estrategica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.market import MarketCandle
from app.services.indicators.rsi  import calculate_rsi
from app.services.indicators.ema  import calculate_ema
from app.services.indicators.macd import calculate_macd
from app.services.indicators.atr  import calculate_atr
from app.services.analysis.analysis_engine import analyze
from app.services.analysis.signal_engine   import generate_signal
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


# ── Tipos ─────────────────────────────────────────────────────────────────────

@dataclass
class BacktestTrade:
    symbol:       str
    entry_idx:    int
    entry_price:  float
    entry_time:   datetime
    side:         str      = "LONG"    # "LONG" | "SHORT"
    exit_price:   float    = 0.0
    exit_time:    Optional[datetime] = None
    pnl:          float    = 0.0
    pnl_pct:      float    = 0.0
    close_reason: str      = ""
    # Phase 12 — Trade Management fields
    break_even_activated: bool           = False
    trailing_active:      bool           = False
    trailing_peak:        Optional[float] = None
    trailing_stop_price:  Optional[float] = None
    tp1_hit:              bool           = False
    tp1_partial_pnl:      float          = 0.0  # PnL da saída parcial
    remaining_qty:        Optional[float] = None


@dataclass
class BacktestResult:
    symbol:         str
    timeframe:      str
    period_days:    int
    candles_used:   int

    # Totais
    total_trades:   int
    winning_trades: int
    losing_trades:  int
    win_rate:       float

    # Separado por lado
    long_trades:    int    = 0
    short_trades:   int    = 0
    win_rate_long:  float  = 0.0
    win_rate_short: float  = 0.0
    pnl_long:       float  = 0.0
    pnl_short:      float  = 0.0

    # Financeiro
    total_pnl:     float   = 0.0
    total_pnl_pct: float   = 0.0
    avg_gain:      float   = 0.0
    avg_loss:      float   = 0.0
    profit_factor: float   = 0.0
    max_drawdown:  float   = 0.0

    started_at:    datetime = field(default_factory=datetime.utcnow)
    finished_at:   datetime = field(default_factory=datetime.utcnow)
    trades:        list[dict] = field(default_factory=list)


# ── Duck-type indicator holder ────────────────────────────────────────────────

class _IndicatorSnapshot:
    __slots__ = (
        "rsi","ema_9","ema_21","ema_50","ema_200",
        "macd","macd_signal","macd_histogram","atr",
    )
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ── Backtest Engine ───────────────────────────────────────────────────────────

class BacktestEngine:

    TIMEFRAME = "1h"

    PERIOD_CANDLE_MAP = {
        7:   7   * 24,
        30:  30  * 24,
        90:  90  * 24,
        180: 180 * 24,
    }

    async def run(
        self,
        symbol:      str,
        period_days: int,
    ) -> BacktestResult:
        started_at = datetime.now(timezone.utc)

        needed      = self.PERIOD_CANDLE_MAP.get(period_days, period_days * 24)
        fetch_limit = needed + 220  # warm-up para EMA-200

        candles = await self._fetch_candles(symbol, self.TIMEFRAME, fetch_limit)

        if len(candles) < 35:
            logger.warning(f"[Backtest] Poucos candles para {symbol}: {len(candles)}")
            return self._empty_result(symbol, period_days, len(candles), started_at)

        candles_period = candles[-needed:] if len(candles) > needed else candles

        trades = self._simulate(candles, candles_period)

        result = self._build_result(
            symbol, period_days, len(candles_period), trades, started_at
        )

        logger.info(
            f"[Backtest] {symbol} {period_days}d — "
            f"{result.total_trades} trades "
            f"(L={result.long_trades} S={result.short_trades}), "
            f"WR={result.win_rate:.1f}%, "
            f"pnl={result.total_pnl:+.4f}"
        )
        return result

    # ── Simulacao ─────────────────────────────────────────────────────────────

    def _simulate(
        self,
        all_candles:    list,
        period_candles: list,
    ) -> list[BacktestTrade]:
        trades:     list[BacktestTrade] = []
        open_trade: BacktestTrade | None = None

        offset        = len(all_candles) - len(period_candles)
        sl_pct        = settings.paper_stop_loss_percent   / 100
        tp_pct        = settings.paper_take_profit_percent / 100
        tp1_pct       = settings.paper_tp1_pct             / 100
        be_trig_pct   = settings.paper_break_even_trigger_pct / 100
        trail_start   = settings.paper_trailing_start_pct     / 100
        trail_dist    = settings.paper_trailing_distance_pct  / 100
        max_hours     = settings.paper_max_hours_open
        risk_usd      = settings.paper_risk_per_trade

        for i, candle in enumerate(period_candles):
            global_idx  = offset + i
            window      = all_candles[:global_idx + 1]

            if len(window) < 35:
                continue

            ind = self._calc_indicators(window)
            if ind is None:
                continue

            price       = candle.close
            signal      = generate_signal(ind, price)  # sem context nem regime no backtest
            candle_time = datetime.fromtimestamp(candle.timestamp, tz=timezone.utc)

            # ── Fechamento do trade aberto ─────────────────────────────────
            if open_trade is not None:
                entry = open_trade.entry_price
                side  = open_trade.side
                qty   = risk_usd / entry  # unidades aproximadas

                # ── 1. Time Stop ──────────────────────────────────────────
                hours_open = (candle_time - open_trade.entry_time).total_seconds() / 3600
                if hours_open >= max_hours:
                    open_trade = self._close_bt_trade(
                        open_trade, price, candle_time, "TIME_STOP", risk_usd
                    )
                    trades.append(open_trade)
                    open_trade = None
                    continue

                # ── 2. Break Even activation ──────────────────────────────
                if not open_trade.break_even_activated:
                    if side == "LONG" and price >= entry * (1 + be_trig_pct):
                        open_trade.break_even_activated = True
                    elif side == "SHORT" and price <= entry * (1 - be_trig_pct):
                        open_trade.break_even_activated = True

                # ── 3. Effective stop (Hard SL / BE / Trailing) ───────────
                close_reason_stop = "STOP_LOSS"
                if side == "LONG":
                    eff_stop = entry * (1 - sl_pct)
                    if open_trade.break_even_activated and entry > eff_stop:
                        eff_stop = entry
                        close_reason_stop = "BREAK_EVEN_STOP"
                    if (open_trade.trailing_active
                            and open_trade.trailing_stop_price
                            and open_trade.trailing_stop_price > eff_stop):
                        eff_stop = open_trade.trailing_stop_price
                        close_reason_stop = "TRAILING_STOP"
                    stop_hit = price <= eff_stop
                else:
                    eff_stop = entry * (1 + sl_pct)
                    if open_trade.break_even_activated and entry < eff_stop:
                        eff_stop = entry
                        close_reason_stop = "BREAK_EVEN_STOP"
                    if (open_trade.trailing_active
                            and open_trade.trailing_stop_price
                            and open_trade.trailing_stop_price < eff_stop):
                        eff_stop = open_trade.trailing_stop_price
                        close_reason_stop = "TRAILING_STOP"
                    stop_hit = price >= eff_stop

                if stop_hit:
                    open_trade = self._close_bt_trade(
                        open_trade, price, candle_time, close_reason_stop, risk_usd
                    )
                    trades.append(open_trade)
                    open_trade = None
                    continue

                # ── 4. Trailing Stop update ───────────────────────────────
                if side == "LONG":
                    should_trail = price >= entry * (1 + trail_start)
                else:
                    should_trail = price <= entry * (1 - trail_start)

                if should_trail or open_trade.trailing_active:
                    if side == "LONG":
                        peak = max(open_trade.trailing_peak or entry, price)
                        t_stop = round(peak * (1 - trail_dist), 8)
                    else:
                        peak = min(open_trade.trailing_peak or entry, price)
                        t_stop = round(peak * (1 + trail_dist), 8)
                    open_trade.trailing_active    = True
                    open_trade.trailing_peak       = peak
                    open_trade.trailing_stop_price = t_stop

                # ── 5. Partial TP1 ────────────────────────────────────────
                if not open_trade.tp1_hit:
                    if side == "LONG" and price >= entry * (1 + tp1_pct):
                        partial_pnl = risk_usd * 0.5 * (price - entry) / entry
                        open_trade.tp1_hit         = True
                        open_trade.tp1_partial_pnl = round(partial_pnl, 6)
                        open_trade.remaining_qty   = qty * 0.5
                        # Trade permanece aberto com 50% da qty

                # ── 6. TP2 (full close) ───────────────────────────────────
                if side == "LONG":
                    hit_tp = price >= entry * (1 + tp_pct)
                    close_sig = signal.signal == "SELL"
                else:
                    hit_tp = price <= entry * (1 - tp_pct)
                    close_sig = signal.signal == "BUY"

                reason = None
                if hit_tp:
                    reason = "TAKE_PROFIT"
                elif close_sig:
                    reason = "SIGNAL_CLOSE"

                if reason:
                    open_trade = self._close_bt_trade(
                        open_trade, price, candle_time, reason, risk_usd
                    )
                    trades.append(open_trade)
                    open_trade = None
                    continue

            # ── Abertura de novo trade ─────────────────────────────────────
            if open_trade is None and signal.confidence >= 70:
                if signal.signal == "BUY":
                    open_trade = BacktestTrade(
                        symbol      = candle.symbol,
                        entry_idx   = global_idx,
                        entry_price = price,
                        entry_time  = candle_time,
                        side        = "LONG",
                    )
                elif signal.signal == "SELL":
                    open_trade = BacktestTrade(
                        symbol      = candle.symbol,
                        entry_idx   = global_idx,
                        entry_price = price,
                        entry_time  = candle_time,
                        side        = "SHORT",
                    )

        # Trade ainda aberto no fim do periodo
        if open_trade is not None and period_candles:
            last_candle = period_candles[-1]
            last_price  = last_candle.close
            last_time   = datetime.fromtimestamp(last_candle.timestamp, tz=timezone.utc)
            open_trade  = self._close_bt_trade(
                open_trade, last_price, last_time, "END_OF_PERIOD", risk_usd
            )
            trades.append(open_trade)

        return trades

    def _close_bt_trade(
        self,
        trade:      BacktestTrade,
        exit_price: float,
        exit_time:  datetime,
        reason:     str,
        risk_usd:   float,
    ) -> BacktestTrade:
        entry = trade.entry_price
        if trade.side == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        # Phase 12: se TP1 foi ativado, a posição final é 50% do risco
        effective_risk = risk_usd * 0.5 if trade.tp1_hit else risk_usd
        pnl = effective_risk * (pnl_pct / 100)

        # Adiciona PnL parcial já realizado no TP1
        total_pnl = round(pnl + trade.tp1_partial_pnl, 6)
        total_pnl_pct = round(
            (total_pnl / risk_usd * 100) if risk_usd > 0 else pnl_pct, 4
        )

        trade.exit_price   = exit_price
        trade.exit_time    = exit_time
        trade.pnl          = total_pnl
        trade.pnl_pct      = total_pnl_pct
        trade.close_reason = reason
        return trade

    # ── Indicadores ───────────────────────────────────────────────────────────

    def _calc_indicators(self, window: list) -> _IndicatorSnapshot | None:
        closes = [c.close for c in window]
        highs  = [c.high  for c in window]
        lows   = [c.low   for c in window]

        rsi           = calculate_rsi(closes)
        ema_9         = calculate_ema(closes, 9)
        ema_21        = calculate_ema(closes, 21)
        ema_50        = calculate_ema(closes, 50)
        ema_200       = calculate_ema(closes, 200)
        macd, sig, h  = calculate_macd(closes)
        atr           = calculate_atr(highs, lows, closes)

        return _IndicatorSnapshot(
            rsi=rsi, ema_9=ema_9, ema_21=ema_21,
            ema_50=ema_50, ema_200=ema_200,
            macd=macd, macd_signal=sig, macd_histogram=h, atr=atr,
        )

    # ── Banco ─────────────────────────────────────────────────────────────────

    async def _fetch_candles(self, symbol: str, timeframe: str, limit: int) -> list:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MarketCandle)
                .where(
                    MarketCandle.symbol    == symbol,
                    MarketCandle.timeframe == timeframe,
                )
                .order_by(MarketCandle.timestamp.desc())
                .limit(limit)
            )
            return list(reversed(result.scalars().all()))

    # ── Resultado ─────────────────────────────────────────────────────────────

    def _build_result(
        self,
        symbol:       str,
        period_days:  int,
        candles_used: int,
        trades:       list[BacktestTrade],
        started_at:   datetime,
    ) -> BacktestResult:
        wins   = [t for t in trades if t.pnl >= 0]
        losses = [t for t in trades if t.pnl <  0]

        longs  = [t for t in trades if t.side == "LONG"]
        shorts = [t for t in trades if t.side == "SHORT"]

        wins_long  = [t for t in longs  if t.pnl >= 0]
        wins_short = [t for t in shorts if t.pnl >= 0]

        total_pnl    = sum(t.pnl for t in trades)
        gross_profit = sum(t.pnl for t in wins)
        gross_loss   = abs(sum(t.pnl for t in losses))

        win_rate       = (len(wins)       / len(trades) * 100) if trades else 0.0
        win_rate_long  = (len(wins_long)  / len(longs)  * 100) if longs  else 0.0
        win_rate_short = (len(wins_short) / len(shorts) * 100) if shorts else 0.0

        profit_factor = (
            gross_profit / gross_loss if gross_loss > 0
            else (float("inf") if gross_profit > 0 else 0.0)
        )

        avg_gain = (gross_profit / len(wins))   if wins   else 0.0
        avg_loss = (gross_loss   / len(losses)) if losses else 0.0

        # Max Drawdown (equity curve)
        balance = settings.paper_initial_balance
        peak    = balance
        max_dd  = 0.0
        for t in sorted(trades, key=lambda x: x.exit_time or datetime.min.replace(tzinfo=timezone.utc)):
            balance += t.pnl
            if balance > peak:
                peak = balance
            dd = ((peak - balance) / peak * 100) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd

        total_pnl_pct = (total_pnl / settings.paper_initial_balance) * 100

        trades_dict = [
            {
                "symbol":       t.symbol,
                "side":         t.side,
                "entry_price":  t.entry_price,
                "exit_price":   t.exit_price,
                "entry_time":   t.entry_time.isoformat() if t.entry_time else None,
                "exit_time":    t.exit_time.isoformat()  if t.exit_time  else None,
                "pnl":          t.pnl,
                "pnl_pct":      t.pnl_pct,
                "close_reason": t.close_reason,
                "result":       "WIN" if t.pnl >= 0 else "LOSS",
            }
            for t in trades
        ]

        return BacktestResult(
            symbol         = symbol,
            timeframe      = self.TIMEFRAME,
            period_days    = period_days,
            candles_used   = candles_used,
            total_trades   = len(trades),
            winning_trades = len(wins),
            losing_trades  = len(losses),
            win_rate       = round(win_rate, 2),
            long_trades    = len(longs),
            short_trades   = len(shorts),
            win_rate_long  = round(win_rate_long, 2),
            win_rate_short = round(win_rate_short, 2),
            pnl_long       = round(sum(t.pnl for t in longs), 6),
            pnl_short      = round(sum(t.pnl for t in shorts), 6),
            total_pnl      = round(total_pnl, 6),
            total_pnl_pct  = round(total_pnl_pct, 4),
            avg_gain       = round(avg_gain, 6),
            avg_loss       = round(avg_loss, 6),
            profit_factor  = round(profit_factor, 4),
            max_drawdown   = round(max_dd, 2),
            started_at     = started_at,
            finished_at    = datetime.now(timezone.utc),
            trades         = trades_dict,
        )

    def _empty_result(
        self, symbol: str, period_days: int, candles_used: int, started_at: datetime
    ) -> BacktestResult:
        return BacktestResult(
            symbol=symbol, timeframe=self.TIMEFRAME, period_days=period_days,
            candles_used=candles_used, total_trades=0, winning_trades=0, losing_trades=0,
            win_rate=0.0, started_at=started_at, finished_at=datetime.now(timezone.utc),
        )


# Singleton
backtest_engine = BacktestEngine()
