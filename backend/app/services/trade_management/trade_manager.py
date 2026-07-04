"""
TradeAI — Trade Manager (Fase 12)

Orquestrador do ciclo de vida da posição após a entrada.
Chamado pelo TradeEngine a cada tick (60s).

Ordem de avaliação (determinística):
  1. Time Stop     — forçado após N horas
  2. Hard SL / BE Stop / Trailing Stop — proteção de capital
  3. Exit Score    — saída por deterioração do contexto
  4. Break Even    — ativação (sem fechar)
  5. Trailing Stop — atualização e verificação de hit
  6. Partial TP1   — saída parcial a +2%
  7. TP2 / Signal Close — saída total

REGRAS:
  - Sem IA generativa
  - Sem SaaS
  - Determinístico
  - Não altera Signal Engine
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.paper_trading import PaperTrade, TradeSide
from app.models.trade_management import TradeLifecycle
from app.logger import get_logger
from app.services.trade_management import (
    time_stop as ts_mod,
    break_even as be_mod,
    trailing_stop as tr_mod,
    partial_tp as ptp_mod,
    exit_score as es_mod,
)

logger = get_logger(__name__)


class TradeManager:
    """
    Avalia o estado de um trade aberto e decide se/como fechá-lo.
    Também atualiza Break Even, Trailing Stop e Partial TP.
    """

    async def evaluate(
        self,
        session: AsyncSession,
        trade: PaperTrade,
        sig_price: float,
        sig_signal: str,
        context: Optional[Any] = None,
        regime: Optional[Any]  = None,
        structure: Optional[Any] = None,
        smc: Optional[Any] = None,
    ) -> Tuple[Optional[str], Optional[float]]:
        """
        Retorna (close_reason, exit_score) ou (None, None).

        close_reason pode ser:
          TIME_STOP | STOP_LOSS | BREAK_EVEN_STOP | TRAILING_STOP
          EXIT_SCORE | PARTIAL_TP (interno) | TAKE_PROFIT | SIGNAL_CLOSE
        """
        now    = datetime.now(timezone.utc)
        price  = sig_price
        entry  = trade.entry_price
        side   = trade.trade_side

        sl_pct = settings.paper_stop_loss_percent / 100

        # ── 1. TIME STOP ──────────────────────────────────────────────────────
        opened_at = trade.opened_at
        if ts_mod.check_time_stop(opened_at, now):
            hrs = ts_mod.hours_open(opened_at, now)
            await self._log(session, trade.id, "TIME_STOP", price,
                            notes=f"{hrs:.1f}h >= {settings.paper_max_hours_open}h")
            return "TIME_STOP", None

        # ── Calcular stop efetivo (Hard SL / BE / Trailing) ───────────────────
        close_reason_stop = "STOP_LOSS"
        if side == TradeSide.LONG.value:
            effective_stop = entry * (1 - sl_pct)
            if trade.break_even_activated and entry > effective_stop:
                effective_stop = entry
                close_reason_stop = "BREAK_EVEN_STOP"
            if (trade.trailing_stop_active and trade.trailing_stop_price
                    and trade.trailing_stop_price > effective_stop):
                effective_stop = trade.trailing_stop_price
                close_reason_stop = "TRAILING_STOP"
            stop_hit = price <= effective_stop
        else:  # SHORT
            effective_stop = entry * (1 + sl_pct)
            if trade.break_even_activated and entry < effective_stop:
                effective_stop = entry
                close_reason_stop = "BREAK_EVEN_STOP"
            if (trade.trailing_stop_active and trade.trailing_stop_price
                    and trade.trailing_stop_price < effective_stop):
                effective_stop = trade.trailing_stop_price
                close_reason_stop = "TRAILING_STOP"
            stop_hit = price >= effective_stop

        if stop_hit:
            await self._log(session, trade.id, close_reason_stop, price,
                            notes=f"stop={effective_stop:.4f}")
            return close_reason_stop, None

        # ── 3. EXIT SCORE ─────────────────────────────────────────────────────
        exit_score = es_mod.compute_exit_score(
            side=side, entry_price=entry, current_price=price,
            context=context, regime=regime, structure=structure, smc=smc,
        )
        if es_mod.should_exit(exit_score):
            await self._log(session, trade.id, "EXIT_SCORE", price,
                            notes=f"score={exit_score:.1f} < {settings.paper_exit_score_threshold}")
            return "EXIT_SCORE", exit_score

        # ── 4. BREAK EVEN activation (sem fechar) ─────────────────────────────
        if be_mod.should_activate(side, entry, price, bool(trade.break_even_activated)):
            trade.break_even_activated = True
            trade.break_even_timestamp = now
            await self._log(session, trade.id, "BREAK_EVEN_ACTIVATED", entry,
                            notes=f"trigger={settings.paper_break_even_trigger_pct}%")
            logger.info(f"[TM] BE ativado {trade.symbol} {side} entry={entry:.4f}")

        # ── 5. TRAILING STOP update ───────────────────────────────────────────
        tr_state = tr_mod.compute(
            side=side, entry_price=entry, current_price=price,
            current_peak=trade.trailing_stop_peak,
            current_stop=trade.trailing_stop_price,
            currently_active=bool(trade.trailing_stop_active),
        )
        if tr_state.active and tr_state.updated:
            trade.trailing_stop_active = True
            trade.trailing_stop_peak   = tr_state.peak
            trade.trailing_stop_price  = tr_state.stop_price
            await self._log(
                session, trade.id, "TRAILING_UPDATED",
                tr_state.stop_price,
                notes=f"peak={tr_state.peak:.4f} dist={settings.paper_trailing_distance_pct}%",
            )

        # ── 6. PARTIAL TP1 ────────────────────────────────────────────────────
        orig_qty = trade.quantity
        ptp = ptp_mod.check(
            side=side, entry_price=entry, current_price=price,
            original_quantity=orig_qty,
            tp1_already_hit=bool(trade.tp1_hit),
        )
        if ptp.tp1_triggered and ptp.partial_qty:
            partial_pnl = ptp_mod.calc_partial_pnl(side, entry, price, ptp.partial_qty)
            trade.tp1_hit           = True
            trade.tp1_hit_timestamp = now
            trade.tp1_partial_qty   = ptp.partial_qty
            trade.tp1_partial_price = price
            trade.remaining_quantity = ptp.remaining_qty
            trade.partial_pnl       = partial_pnl

            # Atualiza saldo com lucro parcial
            await self._update_balance(session, partial_pnl)

            await self._log(
                session, trade.id, "PARTIAL_EXIT", price,
                quantity=ptp.partial_qty, pnl=partial_pnl,
                notes=f"TP1 {settings.paper_tp1_pct}% → {ptp.partial_qty:.6f} units",
            )
            logger.info(
                f"[TM] PARTIAL TP1 {trade.symbol} {side} @ {price:.4f} "
                f"qty={ptp.partial_qty:.6f} pnl={partial_pnl:+.4f}"
            )
            return None, exit_score  # mantém aberto com qty restante

        # ── 7. TP2 (full close) ───────────────────────────────────────────────
        if ptp.tp2_triggered:
            await self._log(session, trade.id, "TAKE_PROFIT", price)
            return "TAKE_PROFIT", exit_score

        # ── 8. SIGNAL CLOSE ───────────────────────────────────────────────────
        if side == TradeSide.LONG.value and sig_signal == "SELL":
            await self._log(session, trade.id, "SIGNAL_CLOSE", price)
            return "SIGNAL_CLOSE", exit_score
        if side == TradeSide.SHORT.value and sig_signal == "BUY":
            await self._log(session, trade.id, "SIGNAL_CLOSE", price)
            return "SIGNAL_CLOSE", exit_score

        return None, exit_score

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _log(
        self,
        session: AsyncSession,
        trade_id: int,
        event_type: str,
        price: Optional[float],
        quantity: Optional[float] = None,
        pnl: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> None:
        event = TradeLifecycle(
            trade_id   = trade_id,
            event_type = event_type,
            price      = price,
            quantity   = quantity,
            pnl        = pnl,
            notes      = notes,
        )
        session.add(event)

    async def _update_balance(
        self, session: AsyncSession, pnl: float
    ) -> None:
        from sqlalchemy import select
        from app.models.paper_trading import PaperAccount
        result  = await session.execute(select(PaperAccount).limit(1))
        account = result.scalar_one_or_none()
        if account:
            account.balance    = round(account.balance + pnl, 6)
            account.updated_at = datetime.now(timezone.utc)


# Singleton
trade_manager = TradeManager()
