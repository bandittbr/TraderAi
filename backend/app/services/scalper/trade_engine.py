"""
Scalper Trade Engine (Fase 13)
Gestão de trades com SL/TP/BE/Trailing Stop.
Completamente isolado do Paper Trading engine.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.scalper import ScalperTrade, ScalperAccount, ScalperRiskDaily
from app.services.scalper.signal_engine import ScalperSignalResult
from app.services.scalper.risk_manager import scalper_risk
from app.logger import logger

# ── Configurações ─────────────────────────────────────────────────────────────
RISK_USD_PER_TRADE  = 10.0     # USD arriscado por trade
SL_PCT              = 0.0025   # 0.25%
TP_PCT              = 0.0050   # 0.50%
BE_TRIGGER_PCT      = 0.0020   # BE ativa em +0.20%
TRAILING_TRIGGER_PCT = 0.0040  # Trailing ativa em +0.40%
TRAILING_DIST_PCT   = 0.0015   # Distância trailing 0.15%
MAX_TRADE_MINUTES   = 120      # Time stop: 2h

INITIAL_BALANCE     = 10_000.0


class ScalperTradeEngine:

    _signals_processed:  int = 0
    _last_execution: datetime | None = None

    # ── Conta ─────────────────────────────────────────────────────────────────
    async def _get_or_create_account(self, session) -> ScalperAccount:
        acc = await session.scalar(select(ScalperAccount))
        if acc is None:
            acc = ScalperAccount(
                balance         = INITIAL_BALANCE,
                initial_balance = INITIAL_BALANCE,
                peak_balance    = INITIAL_BALANCE,
            )
            session.add(acc)
            await session.flush()
        return acc

    # ── Trade aberto para símbolo ─────────────────────────────────────────────
    async def _get_open_trade(self, session, symbol: str) -> ScalperTrade | None:
        return await session.scalar(
            select(ScalperTrade).where(
                ScalperTrade.symbol == symbol,
                ScalperTrade.status == "OPEN",
            )
        )

    # ── Processa sinal ────────────────────────────────────────────────────────
    async def process_signal(self, sig: ScalperSignalResult) -> None:
        ScalperTradeEngine._signals_processed += 1
        ScalperTradeEngine._last_execution     = datetime.now(timezone.utc)

        try:
            async with AsyncSessionLocal() as session:
                open_trade = await self._get_open_trade(session, sig.symbol)

                if open_trade:
                    await self._manage_open_trade(session, open_trade, sig)
                elif sig.direction in ("LONG", "SHORT"):
                    can, reason = await scalper_risk.can_trade()
                    if can:
                        await self._open_trade(session, sig)
                    else:
                        logger.debug(f"[Scalper] {sig.symbol} bloqueado: {reason}")

                await session.commit()

        except Exception as exc:
            logger.error(f"[Scalper TradeEngine] {sig.symbol}: {exc}")

    # ── Abrir trade ───────────────────────────────────────────────────────────
    async def _open_trade(self, session, sig: ScalperSignalResult) -> None:
        price = sig.price
        side  = sig.direction   # LONG / SHORT

        if side == "LONG":
            sl_price = round(price * (1 - SL_PCT), 8)
            tp_price = round(price * (1 + TP_PCT), 8)
            be_price = round(price * (1 + BE_TRIGGER_PCT), 8)
        else:
            sl_price = round(price * (1 + SL_PCT), 8)
            tp_price = round(price * (1 - TP_PCT), 8)
            be_price = round(price * (1 - BE_TRIGGER_PCT), 8)

        qty = round(RISK_USD_PER_TRADE / (price * SL_PCT), 6)

        trade = ScalperTrade(
            symbol           = sig.symbol,
            timeframe_entry  = "1m",
            trade_side       = side,
            trend_15m        = sig.trend_15m,
            confirm_5m       = sig.confirm_5m,
            confidence       = sig.confidence,
            entry_price      = price,
            quantity         = qty,
            risk_usd         = RISK_USD_PER_TRADE,
            stop_loss_price  = sl_price,
            take_profit_price= tp_price,
            break_even_price = be_price,
            status           = "OPEN",
        )
        session.add(trade)
        logger.info(
            f"[Scalper] ABERTO {sig.symbol} {side} @ {price:.4f} "
            f"SL={sl_price:.4f} TP={tp_price:.4f} conf={sig.confidence:.0f}%"
        )

    # ── Gerenciar trade aberto ────────────────────────────────────────────────
    async def _manage_open_trade(
        self, session, trade: ScalperTrade, sig: ScalperSignalResult
    ) -> None:
        price = sig.price
        side  = trade.trade_side
        now   = datetime.now(timezone.utc)

        # PnL atual
        if side == "LONG":
            pnl_pct = (price - trade.entry_price) / trade.entry_price
        else:
            pnl_pct = (trade.entry_price - price) / trade.entry_price

        # ── 1. Time Stop ──────────────────────────────────────────────────────
        minutes_open = (now - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
        if minutes_open >= MAX_TRADE_MINUTES:
            await self._close_trade(session, trade, price, "TIME_STOP", pnl_pct, now)
            return

        # ── 2. Take Profit ────────────────────────────────────────────────────
        if side == "LONG" and price >= trade.take_profit_price:
            await self._close_trade(session, trade, price, "TAKE_PROFIT", pnl_pct, now)
            return
        if side == "SHORT" and price <= trade.take_profit_price:
            await self._close_trade(session, trade, price, "TAKE_PROFIT", pnl_pct, now)
            return

        # ── 3. Stop Loss ──────────────────────────────────────────────────────
        if side == "LONG" and price <= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return
        if side == "SHORT" and price >= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return

        # ── 4. Break Even ─────────────────────────────────────────────────────
        if not trade.break_even_activated:
            be_hit = (side == "LONG" and price >= trade.break_even_price) or \
                     (side == "SHORT" and price <= trade.break_even_price)
            if be_hit:
                trade.break_even_activated = True
                trade.stop_loss_price      = trade.entry_price  # BE = entrada
                logger.debug(f"[Scalper] {trade.symbol} Break Even ativado @ {price:.4f}")

        # ── 5. Trailing Stop ──────────────────────────────────────────────────
        trailing_hit = (side == "LONG" and price >= trade.entry_price * (1 + TRAILING_TRIGGER_PCT)) or \
                       (side == "SHORT" and price <= trade.entry_price * (1 - TRAILING_TRIGGER_PCT))

        if trailing_hit or trade.trailing_stop_active:
            if not trade.trailing_stop_active:
                trade.trailing_stop_active = True
                if side == "LONG":
                    trade.trailing_stop_peak  = price
                    trade.trailing_stop_price = round(price * (1 - TRAILING_DIST_PCT), 8)
                else:
                    trade.trailing_stop_peak  = price
                    trade.trailing_stop_price = round(price * (1 + TRAILING_DIST_PCT), 8)
                logger.debug(f"[Scalper] {trade.symbol} Trailing Stop ativado @ {price:.4f}")
            else:
                # Atualiza peak e trailing price
                if side == "LONG" and price > (trade.trailing_stop_peak or 0):
                    trade.trailing_stop_peak  = price
                    trade.trailing_stop_price = round(price * (1 - TRAILING_DIST_PCT), 8)
                elif side == "SHORT" and price < (trade.trailing_stop_peak or float("inf")):
                    trade.trailing_stop_peak  = price
                    trade.trailing_stop_price = round(price * (1 + TRAILING_DIST_PCT), 8)

                # Verifica hit
                ts_price = trade.trailing_stop_price or 0
                if (side == "LONG" and price <= ts_price) or \
                   (side == "SHORT" and price >= ts_price):
                    await self._close_trade(session, trade, price, "TRAILING_STOP", pnl_pct, now)
                    return

        # ── 6. Sinal inverso (opcional) ───────────────────────────────────────
        reverse = (side == "LONG" and sig.direction == "SHORT") or \
                  (side == "SHORT" and sig.direction == "LONG")
        if reverse and sig.confidence >= 65:
            await self._close_trade(session, trade, price, "SIGNAL_CLOSE", pnl_pct, now)

    # ── Fechar trade ──────────────────────────────────────────────────────────
    async def _close_trade(
        self, session, trade: ScalperTrade,
        exit_price: float, reason: str, pnl_pct: float, now: datetime
    ) -> None:
        pnl_usd = round(trade.quantity * (exit_price - trade.entry_price)
                        * (1 if trade.trade_side == "LONG" else -1), 6)
        pnl_pct_rounded = round(pnl_pct * 100, 4)

        trade.exit_price      = exit_price
        trade.pnl             = pnl_usd
        trade.pnl_pct         = pnl_pct_rounded
        trade.status          = "CLOSED"
        trade.close_reason    = reason
        trade.closed_at       = now
        trade.duration_minutes = round(
            (now - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60, 1
        )

        # Atualiza conta
        acc = await self._get_or_create_account(session)
        acc.balance    += pnl_usd
        acc.total_pnl  += pnl_usd
        if acc.balance > acc.peak_balance:
            acc.peak_balance = acc.balance
        acc.updated_at = now

        # Atualiza risco diário (USD)
        from sqlalchemy import select as sa_select
        from app.models.scalper import ScalperRiskDaily
        from datetime import date
        today = date.today().isoformat()
        risk_row = await session.scalar(
            sa_select(ScalperRiskDaily).where(ScalperRiskDaily.date == today)
        )
        if risk_row:
            risk_row.daily_pnl_usd += pnl_usd
            risk_row.updated_at     = now

        won = pnl_usd > 0
        logger.info(
            f"[Scalper] FECHADO {trade.symbol} {trade.trade_side} @ {exit_price:.4f} "
            f"PnL={pnl_usd:+.4f} USD ({pnl_pct_rounded:+.3f}%) motivo={reason}"
        )

        # Registra no risk manager (pnl_pct em %)
        await scalper_risk.record_trade(pnl_pct_rounded, won)

    # ── Debug info ────────────────────────────────────────────────────────────
    async def get_debug_info(self) -> dict:
        async with AsyncSessionLocal() as session:
            acc        = await self._get_or_create_account(session)
            open_count = await session.scalar(
                select(ScalperTrade).where(ScalperTrade.status == "OPEN")
            )
        await scalper_risk.load_today()
        return {
            "signals_processed":    self._signals_processed,
            "last_execution":       self._last_execution.isoformat() if self._last_execution else None,
            "balance":              acc.balance,
            "total_pnl":           acc.total_pnl,
            "peak_balance":        acc.peak_balance,
            "risk_blocked":        scalper_risk.is_blocked,
            "consecutive_losses":  scalper_risk.consecutive_losses,
            "daily_pnl_pct":       scalper_risk.daily_pnl_pct,
        }


scalper_engine = ScalperTradeEngine()
