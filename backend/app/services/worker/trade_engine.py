"""
Worker Trade Engine — 24/7 Multi-Timeframe Agent (V7)

Worker é o agente mais sofisticado:
  - Direção: timeframe 1h (EMA + structure + SMC)
  - Entrada: timeframe 15m (pullback, FVG, sweep, RSI)
  - 3 níveis de TP (R:R 1.5, 3.0, 5.0)
  - Trailing stop após TP1
  - Alavancagem adaptativa (1x-3x)
  - Fee modeling e circuit breaker

Integrado ao scheduler principal.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, desc

from app.database import AsyncSessionLocal
from app.models.worker import WorkerTrade, WorkerAccount, WorkerRiskDaily
from app.services.worker.signal_engine import WorkerSignalEngine, WorkerSignalResult
from app.services.worker.risk_manager import worker_risk
from app.services.signal_analytics.signal_tracker import signal_tracker

logger = logging.getLogger(__name__)

# ── Configurações ─────────────────────────────────────────────────────────────
RISK_PER_TRADE_PCT  = 1.0    # 1% do saldo arriscado por trade
MAX_OPEN_TRADES     = 3      # máx posições simultâneas
MAX_TRADE_MINUTES   = 480    # time stop: 8h
INITIAL_BALANCE     = 10_000.0
BASE_SL_PCT         = 0.005  # 0.5% mínimo

# Fee modeling (mesmo do scalper)
WORKER_FEE_PER_LEG  = 0.0006  # 0.06% taker
WORKER_SLIPPAGE_LEG = 0.0002  # 0.02% slippage
WORKER_FEE_TOTAL    = (WORKER_FEE_PER_LEG + WORKER_SLIPPAGE_LEG) * 2  # 0.16%


class WorkerTradeEngine:
    """
    Engine principal do Worker Agent.
    Processa sinais, executa trades, gerencia SL/TP/BE/Trailing/TP parcial.
    """

    _last_execution: datetime | None = None

    def __init__(self):
        self.signal_engine = WorkerSignalEngine()

    # ── Processar sinal do scheduler ───────────────────────────────────────

    async def process_signal(
        self,
        symbol:     str,
        price_1h:   Any,           # MarketIndicator 1h
        price_15m:  Any,           # MarketIndicator 15m
        regime:     Any = None,
        context:    Any = None,
        structure:  Any = None,
        smc:        Any = None,
        weights:    Optional[dict] = None,
        current_price: Optional[float] = None,
    ) -> None:
        """Processa dados de mercado e decide se abre/fecha trades."""
        try:
            WorkerTradeEngine._last_execution = datetime.now(timezone.utc)
            # Gera sinal multi-timeframe
            sig = await self.signal_engine.analyze(
                symbol=symbol, price_1h=price_1h, price_15m=price_15m,
                regime=regime, context=context,
                structure=structure, smc=smc, weights=weights,
                current_price=current_price,
            )

            # Gerencia trades abertos (SL/TP/BE/Trailing)
            async with AsyncSessionLocal() as session:
                open_trades = await self._get_open_trades(session, symbol)
                for trade in open_trades:
                    await self._manage_open_trade(session, trade, sig)

                # Abre novo trade se sinal válido (1 posição por símbolo)
                total_open = await self._get_open_trades(session)
                if sig.is_valid and not open_trades and len(total_open) < MAX_OPEN_TRADES:
                    await self._open_trade(session, sig, symbol)
                await session.commit()

        except Exception as exc:
            logger.error(f"[Worker] process_signal({symbol}) error: {exc}", exc_info=True)

    # ── Abrir trade ────────────────────────────────────────────────────────

    async def _open_trade(
        self, session, sig: WorkerSignalResult, symbol: str,
    ) -> Optional[int]:
        """Abre novo trade. Retorna ID ou None."""
        can_trade, reason = worker_risk.can_trade(sig.regime)
        if not can_trade:
            logger.info(f"[Worker] Trade bloqueado: {reason}")
            return None

        # Saldo e sizing
        acc = await self._get_or_create_account(session)
        sizing_factor = worker_risk.sizing_factor(sig.regime)

        trade_value = acc.balance * (RISK_PER_TRADE_PCT / 100) * sizing_factor
        risk_per_unit = abs(sig.entry_price - sig.stop_loss)
        if risk_per_unit <= 0:
            return None

        # FIX: leverage NÃO entra no sizing — já é aplicada no cálculo do PnL.
        # (Antes: qty × lev e PnL × lev → perda no SL = 1% × lev², até 9% com 3x)
        # Agora: SL atingido perde exatamente 1% × leverage do saldo.
        quantity = trade_value / risk_per_unit
        quantity = max(0.000001, round(quantity, 6))

        trade = WorkerTrade(
            symbol          = symbol,
            timeframe_entry = "15m",
            trade_side      = sig.direction,
            entry_price     = sig.entry_price,
            quantity        = quantity,
            leverage        = sig.leverage,
            stop_loss_price = sig.stop_loss,
            take_profit1_price = sig.take_profit1,
            take_profit2_price = sig.take_profit2,
            take_profit3_price = sig.take_profit3,
            confidence      = sig.confidence,
            regime_at_entry = sig.regime,
            volatility_at_entry = sig.atr_pct,
            direction_score = sig.direction_score,
            entry_reason    = sig.reason[:100] if sig.reason else None,
            status          = "OPEN",
            opened_at       = datetime.now(timezone.utc),
        )
        session.add(trade)
        await session.flush()

        # Auto-trading: send signal to broker if enabled
        try:
            from app.services.broker.engine import broker_engine
            await broker_engine.process_agent_signal(
                "default", "worker",
                {"symbol": symbol, "side": sig.direction, "confidence": sig.confidence,
                 "regime": sig.regime, "entry_price": sig.entry_price,
                 "stop_loss": sig.stop_loss, "take_profit": sig.take_profit1,
                 "quantity": quantity}
            )
        except Exception as auto_err:
            logger.warning(f"[Worker] Auto-trading signal failed: {auto_err}", exc_info=True)

        # Atualiza conta
        acc.total_trades += 1
        acc.updated_at = datetime.now(timezone.utc)

        # Registra sinal no signal_tracker
        try:
            await signal_tracker.record_signal(
                symbol=symbol, timeframe="15m",
                signal=sig.direction,
                confidence=sig.confidence,
                indicator=type("obj", (), {"rsi": 50, "close": sig.entry_price})(),
                current_price=sig.entry_price,
            )
        except Exception as e:
            logger.warning(f"[Worker] Falha ao registrar sinal no signal_tracker: {e}", exc_info=True)

        logger.info(
            f"[Worker] ABERTO {sig.direction} {symbol} @ {sig.entry_price:.2f} "
            f"qty={quantity:.6f} lev={sig.leverage}x SL={sig.stop_loss:.2f} "
            f"TP1={sig.take_profit1:.2f} conf={sig.confidence:.0f}%"
        )

        # Log de atividade + broadcast WebSocket
        try:
            from app.services.trade_activity import log_activity
            await log_activity(
                agent="worker",
                event="open",
                symbol=symbol,
                price=sig.entry_price,
                trade_id=trade.id,
                quantity=quantity,
                side=sig.direction,
                confidence=sig.confidence,
                regime=getattr(sig, "regime", None),
                balance_after=acc.balance,
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar abertura worker: {e}")

        return trade.id

    # ── Gerenciar trade aberto ─────────────────────────────────────────────

    async def _manage_open_trade(
        self, session, trade: WorkerTrade, sig: WorkerSignalResult,
    ) -> None:
        """Verifica SL/TP/BE/Trailing para um trade aberto."""
        price = sig.entry_price  # preço atual
        if not price or price <= 0:
            return  # FIX: sinal sem preço válido fechava trade no SL com preço 0
        side = trade.trade_side
        now = datetime.now(timezone.utc)

        # PnL atual
        if side == "LONG":
            pnl_pct = (price - trade.entry_price) / trade.entry_price
        else:
            pnl_pct = (trade.entry_price - price) / trade.entry_price

        # ── 1. Time Stop ──
        minutes_open = (now - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
        if minutes_open >= MAX_TRADE_MINUTES:
            await self._close_trade(session, trade, price, "TIME_STOP", pnl_pct, now)
            return

        # ── 2. Stop Loss ──
        if side == "LONG" and price <= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return
        if side == "SHORT" and price >= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return

        # ── 3. Take Profits (parciais) ──
        if not trade.partial_tp1_hit and trade.take_profit1_price:
            hit = (side == "LONG" and price >= trade.take_profit1_price) or \
                  (side == "SHORT" and price <= trade.take_profit1_price)
            if hit:
                trade.partial_tp1_hit = True
                logger.info(f"[Worker] TP1 batido {trade.symbol} @ {price:.2f}")
                # Activa trailing após TP1
                if not trade.trailing_stop_active:
                    trade.trailing_stop_active = True
                    trade.trailing_stop_peak = price
                    trade.trailing_stop_price = round(
                        price * (0.995 if side == "LONG" else 1.005), 8
                    )

        if not trade.partial_tp2_hit and trade.take_profit2_price:
            hit = (side == "LONG" and price >= trade.take_profit2_price) or \
                  (side == "SHORT" and price <= trade.take_profit2_price)
            if hit:
                trade.partial_tp2_hit = True
                logger.info(f"[Worker] TP2 batido {trade.symbol} @ {price:.2f}")

        if trade.take_profit3_price:
            hit = (side == "LONG" and price >= trade.take_profit3_price) or \
                  (side == "SHORT" and price <= trade.take_profit3_price)
            if hit:
                await self._close_trade(session, trade, price, "TAKE_PROFIT3", pnl_pct, now)
                return

        # ── 4. Break Even ──
        if not trade.break_even_activated:
            be_hit = (side == "LONG" and price >= trade.entry_price * 1.005) or \
                     (side == "SHORT" and price <= trade.entry_price * 0.995)
            if be_hit:
                trade.break_even_activated = True
                # BE cobre taxas (0.16% round-trip) — fechar no BE = net ~0, não -0.16%
                if side == "LONG":
                    trade.stop_loss_price = round(trade.entry_price * (1 + WORKER_FEE_TOTAL), 8)
                else:
                    trade.stop_loss_price = round(trade.entry_price * (1 - WORKER_FEE_TOTAL), 8)
                logger.debug(f"[Worker] BE ativado {trade.symbol} @ {price:.2f}")

        # ── 5. Trailing Stop ──
        if trade.trailing_stop_active:
            if side == "LONG" and price > (trade.trailing_stop_peak or 0):
                trade.trailing_stop_peak = price
                trade.trailing_stop_price = round(price * 0.995, 8)
            elif side == "SHORT" and price < (trade.trailing_stop_peak or float("inf")):
                trade.trailing_stop_peak = price
                trade.trailing_stop_price = round(price * 1.005, 8)

            ts_price = trade.trailing_stop_price or 0
            if (side == "LONG" and price <= ts_price) or \
               (side == "SHORT" and price >= ts_price):
                await self._close_trade(session, trade, price, "TRAILING_STOP", pnl_pct, now)
                return

    # ── Fechar trade ───────────────────────────────────────────────────────

    async def _close_trade(
        self, session, trade: WorkerTrade,
        exit_price: float, reason: str, pnl_pct: float, now: datetime,
    ) -> None:
        """Fecha o trade e atualiza conta com fee modeling."""
        side = trade.trade_side
        pnl_usd = round(
            trade.quantity * (exit_price - trade.entry_price)
            * (1 if side == "LONG" else -1) * trade.leverage, 6
        )
        pnl_pct_rounded = round(pnl_pct * 100 * trade.leverage, 4)
        fee_pct = round(WORKER_FEE_TOTAL * 100, 4)
        net_pnl = round(pnl_pct_rounded - fee_pct, 4)

        trade.exit_price = exit_price
        trade.pnl = pnl_usd
        trade.pnl_pct = pnl_pct_rounded
        trade.fee_cost_pct = fee_pct
        trade.net_pnl_pct = net_pnl
        trade.status = "CLOSED"
        trade.close_reason = reason
        trade.closed_at = now
        trade.duration_minutes = round(
            (now - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60, 1
        )

        # Atualiza conta
        acc = await self._get_or_create_account(session)
        fee_usd = round(trade.quantity * trade.entry_price * WORKER_FEE_TOTAL * trade.leverage, 6)
        pnl_net_usd = pnl_usd - fee_usd
        acc.balance += pnl_net_usd
        acc.total_pnl += pnl_net_usd
        if acc.balance > acc.peak_balance:
            acc.peak_balance = acc.balance
        if net_pnl > 0:
            acc.winning_trades += 1
        else:
            acc.losing_trades += 1
        acc.updated_at = now

        # Registra no risk manager
        won = net_pnl > 0
        regime = getattr(trade, "regime_at_entry", "UNKNOWN")
        worker_risk.record_trade(won, regime=regime)

        logger.info(
            f"[Worker] FECHADO {side} {trade.symbol} @ {exit_price:.2f} "
            f"gross={pnl_pct_rounded:+.3f}% net={net_pnl:+.3f}% "
            f"lev={trade.leverage}x motivo={reason}"
        )

        # Log de atividade + broadcast WebSocket
        try:
            from app.services.trade_activity import log_activity
            await log_activity(
                agent="worker",
                event="close",
                symbol=trade.symbol,
                price=exit_price,
                trade_id=trade.id,
                quantity=trade.quantity,
                side=side,
                pnl=round(pnl_net_usd, 6),
                pnl_pct=net_pnl,  # FIX: net_pnl já está em % (antes multiplicava ×100 de novo)
                reason=reason,
                regime=getattr(trade, "regime_at_entry", None),
                balance_after=acc.balance,
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar fechamento worker: {e}")

    # ── Helpers ────────────────────────────────────────────────────────────

    async def _get_open_trades(self, session, symbol: Optional[str] = None) -> list[WorkerTrade]:
        q = select(WorkerTrade).where(WorkerTrade.status == "OPEN")
        if symbol:
            q = q.where(WorkerTrade.symbol == symbol)
        result = await session.execute(q)
        return list(result.scalars().all())

    async def _get_or_create_account(self, session) -> WorkerAccount:
        acc = await session.scalar(select(WorkerAccount))
        if acc is None:
            acc = WorkerAccount(
                balance=INITIAL_BALANCE, initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            session.add(acc)
            await session.flush()
            await session.refresh(acc)
        return acc


# Singleton
worker_engine = WorkerTradeEngine()
