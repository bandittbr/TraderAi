"""
Multi-Agent Trade Engine — Executa sinais de todos os agentes.
Cada agente tem sua própria conta e trades.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select, desc

from app.database import AsyncSessionLocal
from app.models.agent_trade import AgentAccount, AgentTrade
from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult
from app.services.agents.registry import agent_registry

logger = logging.getLogger(__name__)

# Configurações
RISK_PER_TRADE_PCT = 1.0    # 1% do saldo por trade
MAX_OPEN_TRADES = 3         # máx posições simultâneas por agente
MAX_TRADE_MINUTES = 480     # time stop: 8h
INITIAL_BALANCE = 100_000.0
FEE_PER_LEG = 0.0006        # 0.06% taker
SLIPPAGE_LEG = 0.0002       # 0.02% slippage
FEE_TOTAL = (FEE_PER_LEG + SLIPPAGE_LEG) * 2  # 0.16%


class MultiAgentEngine:
    """
    Engine principal do sistema multi-agente.
    Processa sinais de todos os agentes registrados.
    """

    async def process_all(self, symbol: str, **kwargs) -> list[AgentResult]:
        """
        Processa todos os agentes habilitados para um símbolo.
        """
        results = []
        for agent in agent_registry.list_enabled():
            try:
                result = await agent.analyze(symbol=symbol, **kwargs)
                agent_registry.store_result(agent.name, result)
                results.append(result)

                # Executa trade se sinal válido
                if result.signal.is_valid:
                    await self._execute_signal(result.signal)
            except Exception as exc:
                logger.error(f"[MultiAgent] {agent.name} error: {exc}", exc_info=True)
                agent_registry.store_result(agent.name, AgentResult(
                    agent_name=agent.name, symbol=symbol,
                    signal=AgentSignal(
                        agent_name=agent.name, symbol=symbol,
                        direction=AgentSide.NEUTRAL, confidence=0,
                        entry_price=0, stop_loss=0, reason=str(exc),
                        is_valid=False,
                    ),
                    error=str(exc),
                ))

        return results

    async def process_agent(self, agent_name: str, symbol: str, **kwargs) -> AgentResult | None:
        """Processa um agente específico."""
        agent = agent_registry.get(agent_name)
        if not agent or not agent.enabled:
            return None
        try:
            result = await agent.analyze(symbol=symbol, **kwargs)
            agent_registry.store_result(agent.name, result)
            if result.signal.is_valid:
                await self._execute_signal(result.signal)
            return result
        except Exception as exc:
            logger.error(f"[MultiAgent] {agent_name} error: {exc}", exc_info=True)
            return AgentResult(
                agent_name=agent_name, symbol=symbol,
                signal=AgentSignal(
                    agent_name=agent_name, symbol=symbol,
                    direction=AgentSide.NEUTRAL, confidence=0,
                    entry_price=0, stop_loss=0, reason=str(exc),
                    is_valid=False,
                ),
                error=str(exc),
            )

    async def manage_open_trades(self, symbol: str, current_price: float) -> None:
        """Gerencia trades abertos de todos os agentes."""
        async with AsyncSessionLocal() as session:
            open_trades = await session.execute(
                select(AgentTrade).where(
                    AgentTrade.status == "OPEN",
                    AgentTrade.symbol == symbol,
                )
            )
            for trade in open_trades.scalars().all():
                await self._manage_trade(session, trade, current_price)
            await session.commit()

    async def _execute_signal(self, sig: AgentSignal) -> None:
        """Executa um sinal de trading."""
        async with AsyncSessionLocal() as session:
            # Verifica trades abertos do agente
            open_trades = await session.execute(
                select(AgentTrade).where(
                    AgentTrade.status == "OPEN",
                    AgentTrade.agent_name == sig.agent_name,
                )
            )
            existing = list(open_trades.scalars().all())

            # Verifica se já tem trade aberto para este símbolo
            existing_symbol = [t for t in existing if t.symbol == sig.symbol]
            if existing_symbol:
                return  # Já tem trade aberto para este símbolo

            if len(existing) >= MAX_OPEN_TRADES:
                return  # Limite de trades abertos

            # Conta do agente
            acc = await self._get_or_create_account(session, sig.agent_name)
            if acc.balance <= 0:
                return

            # Sizing
            trade_value = acc.balance * (RISK_PER_TRADE_PCT / 100)
            risk_per_unit = abs(sig.entry_price - sig.stop_loss)
            if risk_per_unit <= 0:
                return

            quantity = trade_value / risk_per_unit
            quantity = max(0.000001, round(quantity, 6))

            trade = AgentTrade(
                agent_name=sig.agent_name,
                symbol=sig.symbol,
                timeframe_entry="1h",
                trade_side=sig.direction.value,
                entry_price=sig.entry_price,
                quantity=quantity,
                leverage=sig.leverage,
                stop_loss_price=sig.stop_loss,
                take_profit_price=sig.take_profit,
                take_profit2_price=sig.take_profit2,
                take_profit3_price=sig.take_profit3,
                confidence=sig.confidence,
                regime_at_entry=sig.regime,
                volatility_at_entry=sig.atr_pct,
                entry_reason=sig.reason[:200] if sig.reason else None,
                status="OPEN",
                opened_at=datetime.now(timezone.utc),
            )
            session.add(trade)
            await session.flush()

            # Atualiza conta
            acc.total_trades += 1
            acc.updated_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(
                f"[MultiAgent] {sig.agent_name} ABERTO {sig.direction.value} "
                f"{sig.symbol} @ {sig.entry_price:.2f} "
                f"qty={quantity:.6f} lev={sig.leverage}x "
                f"conf={sig.confidence:.0f}% razão={sig.reason[:60]}"
            )

    async def _manage_trade(self, session, trade: AgentTrade, price: float) -> None:
        """Gerencia SL/TP/BE/Trailing de um trade aberto."""
        if not price or price <= 0:
            return

        side = trade.trade_side
        now = datetime.now(timezone.utc)

        # PnL atual
        if side == "LONG":
            pnl_pct = (price - trade.entry_price) / trade.entry_price
        else:
            pnl_pct = (trade.entry_price - price) / trade.entry_price

        # 1. Time Stop
        minutes_open = (now - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60
        if minutes_open >= MAX_TRADE_MINUTES:
            await self._close_trade(session, trade, price, "TIME_STOP", pnl_pct, now)
            return

        # 2. Stop Loss
        if side == "LONG" and price <= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return
        if side == "SHORT" and price >= trade.stop_loss_price:
            await self._close_trade(session, trade, price, "STOP_LOSS", pnl_pct, now)
            return

        # 3. Take Profits
        if not trade.partial_tp1_hit and trade.take_profit_price:
            hit = (side == "LONG" and price >= trade.take_profit_price) or \
                  (side == "SHORT" and price <= trade.take_profit_price)
            if hit:
                trade.partial_tp1_hit = True
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

        if trade.take_profit3_price:
            hit = (side == "LONG" and price >= trade.take_profit3_price) or \
                  (side == "SHORT" and price <= trade.take_profit3_price)
            if hit:
                await self._close_trade(session, trade, price, "TAKE_PROFIT3", pnl_pct, now)
                return

        # 4. Break Even
        if not trade.break_even_activated:
            be_hit = (side == "LONG" and price >= trade.entry_price * 1.005) or \
                     (side == "SHORT" and price <= trade.entry_price * 0.995)
            if be_hit:
                trade.break_even_activated = True
                if side == "LONG":
                    trade.stop_loss_price = round(trade.entry_price * (1 + FEE_TOTAL), 8)
                else:
                    trade.stop_loss_price = round(trade.entry_price * (1 - FEE_TOTAL), 8)

        # 5. Trailing Stop
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

    async def _close_trade(
        self, session, trade: AgentTrade,
        exit_price: float, reason: str, pnl_pct: float, now: datetime,
    ) -> None:
        """Fecha o trade e atualiza conta."""
        side = trade.trade_side
        pnl_usd = round(
            trade.quantity * (exit_price - trade.entry_price)
            * (1 if side == "LONG" else -1) * trade.leverage, 6
        )
        pnl_pct_rounded = round(pnl_pct * 100 * trade.leverage, 4)
        fee_pct = round(FEE_TOTAL * 100, 4)
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
        acc = await self._get_or_create_account(session, trade.agent_name)
        fee_usd = round(trade.quantity * trade.entry_price * FEE_TOTAL * trade.leverage, 6)
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

        logger.info(
            f"[MultiAgent] {trade.agent_name} FECHADO {side} {trade.symbol} "
            f"@ {exit_price:.2f} gross={pnl_pct_rounded:+.3f}% "
            f"net={net_pnl:+.3f}% motivo={reason}"
        )

    async def _get_or_create_account(self, session, agent_name: str) -> AgentAccount:
        acc = await session.scalar(
            select(AgentAccount).where(AgentAccount.agent_name == agent_name)
        )
        if acc is None:
            acc = AgentAccount(
                agent_name=agent_name,
                balance=INITIAL_BALANCE,
                initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            session.add(acc)
            await session.flush()
            await session.refresh(acc)
        return acc


# Singleton
multi_agent_engine = MultiAgentEngine()
