"""
Groq Agent — Trade Engine (V1)
Gerencia trades do Groq Agent: abertura, fechamento, P&L.

Fluxo por ciclo (a cada 60s):
  1. Coleta dados de mercado (indicadores, preço, regime)
  2. Busca posição aberta (se houver)
  3. Envia tudo para o GroqSignalEngine
  4. Executa a decisão (BUY/SELL/HOLD)
  5. Calcula P&L e atualiza conta
  6. Salva thinking log + broadcast WebSocket
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc

from app.database import AsyncSessionLocal
from app.models.groq_agent import GroqTrade, GroqAccount, GroqThinking
from app.services.groq_agent.signal_engine import groq_signal_engine, GroqSignalResult
from app.services.groq_agent.risk_manager import groq_risk
from app.services.trade_activity import log_activity

logger = logging.getLogger(__name__)

# Configurações
INITIAL_BALANCE = 10_000.0
RISK_PER_TRADE_PCT = 0.02  # 2% do saldo (exposição bruta = 2% × 10x = 20% do saldo)
MAX_TRADE_MINUTES = 15     # Time stop: 15 minutos
LEVERAGE = 10.0             # Alavancagem fixa 10x
FEE_TOTAL_PCT = 0.0016      # 0.16% round-trip

# Fee per leg
FEE_PER_LEG = 0.0006
SLIPPAGE_LEG = 0.0002


class GroqTradeEngine:
    """Engine principal do Groq Agent."""

    _signals_processed: int = 0
    _last_execution: Optional[datetime] = None

    async def process_cycle(self, symbol: str = "BTCUSDT") -> None:
        """
        Executa um ciclo completo: coleta dados → LLM decide → executa trade.
        Chamado pelo scheduler a cada 60 segundos.
        """
        try:
            GroqTradeEngine._signals_processed += 1
            GroqTradeEngine._last_execution = datetime.now(timezone.utc)

            # 1. Coletar dados de mercado
            price, indicators, regime = await self._collect_market_data(symbol)
            if price <= 0:
                return

            # 2. Buscar conta e posição aberta
            async with AsyncSessionLocal() as session:
                account = await self._get_or_create_account(session)
                open_trade = await self._get_open_trade(session, symbol)
                recent_trades = await self._get_recent_trades(session, symbol, limit=5)

            # 3. Montar contexto da posição aberta
            open_position = None
            if open_trade:
                open_position = {
                    "side": open_trade.trade_side,
                    "entry_price": open_trade.entry_price,
                    "stop_loss": open_trade.stop_loss_price,
                    "take_profit": open_trade.take_profit_price,
                }

            # 4. Chamar Groq API
            signal = await groq_signal_engine.analyze(
                symbol=symbol,
                price=price,
                indicators=indicators,
                regime=regime,
                recent_trades=recent_trades,
                account_balance=account.balance,
                open_position=open_position,
            )

            # 5. Salvar thinking log
            await self._save_thinking(signal, symbol)

            # 6. Executar decisão
            if not signal.is_valid:
                return

            async with AsyncSessionLocal() as session:
                account = await self._get_or_create_account(session)

                if signal.action == "HOLD":
                    # Verificar time stop na posição aberta
                    if open_trade:
                        await self._check_time_stop(session, open_trade, price)
                    return

                if signal.action == "BUY":
                    if open_trade and open_trade.trade_side == "SHORT":
                        # Fechar SHORT
                        await self._close_trade(
                            session, open_trade, price, "SIGNAL_CLOSE",
                            signal.reasoning,
                        )
                    elif not open_trade:
                        # Abrir LONG
                        await self._open_trade(session, signal, symbol, "LONG", account)

                elif signal.action == "SELL":
                    if open_trade and open_trade.trade_side == "LONG":
                        # Fechar LONG
                        await self._close_trade(
                            session, open_trade, price, "SIGNAL_CLOSE",
                            signal.reasoning,
                        )
                    elif not open_trade:
                        # Abrir SHORT
                        await self._open_trade(session, signal, symbol, "SHORT", account)

                # Verificar SL/TP da posição aberta
                if open_trade:
                    await self._check_sl_tp(session, open_trade, price)

                await session.commit()

        except Exception as e:
            logger.error(f"[Groq] Erro no ciclo: {e}", exc_info=True)

    async def _collect_market_data(self, symbol: str) -> tuple[float, dict, str]:
        """Coleta dados de mercado do banco e do WebSocket."""
        from app.services.market_data.store import store
        from app.services.indicators.calculator import indicator_calculator
        from app.services.signal_analytics.regime_classifier import classify_regime

        # Preço atual
        stat = await store.get_stats(symbol)
        price = stat.price if stat else 0.0

        # Indicadores 1h
        ind = await indicator_calculator.get_latest(symbol, "1h")
        if ind is None or price <= 0:
            return 0.0, {}, "UNKNOWN"

        indicators = {
            "rsi": ind.rsi or 50,
            "ema_9": ind.ema_9 or 0,
            "ema_21": ind.ema_21 or 0,
            "ema_50": ind.ema_50 or 0,
            "ema_200": ind.ema_200 or 0,
            "macd": ind.macd or 0,
            "macd_signal": ind.macd_signal or 0,
            "macd_histogram": ind.macd_histogram or 0,
            "atr": ind.atr or 0,
        }

        # Regime
        regime_result = classify_regime(ind, price)
        regime = regime_result.regime.value if hasattr(regime_result.regime, 'value') else str(regime_result.regime)

        return price, indicators, regime

    async def _open_trade(
        self, session, signal: GroqSignalResult,
        symbol: str, side: str, account: GroqAccount,
    ) -> Optional[GroqTrade]:
        """Abre novo trade alavancado 10x baseado na decisão do LLM."""
        price = signal.price

        # Risk sizing com alavancagem
        # Risco = 2% do saldo. Com 10x alavancagem, o tamanho da posição
        # é calculado para que um movimento de SL resulte em perda de 2% do saldo.
        max_risk = groq_risk.max_risk_usd(account.balance)
        sl_distance = price * (signal.stop_loss_pct / 100)
        if sl_distance <= 0:
            return None

        # Quantidade = risco / distância_SL (já considera que loss = qty × sl_distance)
        quantity = round(max_risk / sl_distance, 6)
        if quantity <= 0:
            return None

        # Calcular SL e TP (percentuais aplicados ao preço)
        if side == "LONG":
            sl_price = round(price * (1 - signal.stop_loss_pct / 100), 8)
            tp_price = round(price * (1 + signal.take_profit_pct / 100), 8)
        else:
            sl_price = round(price * (1 + signal.stop_loss_pct / 100), 8)
            tp_price = round(price * (1 - signal.take_profit_pct / 100), 8)

        trade = GroqTrade(
            symbol=symbol,
            trade_side=side,
            entry_price=price,
            quantity=quantity,
            leverage=LEVERAGE,
            stop_loss_price=sl_price,
            take_profit_price=tp_price,
            confidence=signal.confidence,
            regime_at_entry=signal.market_assessment,
            status="OPEN",
        )
        session.add(trade)
        await session.flush()

        # Auto-trading: send signal to broker if enabled
        try:
            from app.services.broker.engine import broker_engine
            await broker_engine.process_agent_signal(
                "default", "groq",
                {"symbol": symbol, "side": side, "confidence": signal.confidence,
                 "regime": signal.market_assessment, "entry_price": price,
                 "stop_loss": sl_price, "take_profit": tp_price,
                 "quantity": quantity}
            )
        except Exception as auto_err:
            logger.warning(f"[Groq] Auto-trading signal failed: {auto_err}", exc_info=True)

        # Atualizar conta
        account.total_trades += 1
        account.updated_at = datetime.now(timezone.utc)

        logger.info(
            f"[Groq] ABERTO {side} {symbol} @ ${price:,.2f} "
            f"qty={quantity:.6f} lev={LEVERAGE}x SL={sl_price:.4f} TP={tp_price:.4f} "
            f"conf={signal.confidence:.0f}%"
        )

        # Log de atividade
        try:
            await log_activity(
                agent="groq",
                event="open",
                symbol=symbol,
                price=price,
                trade_id=trade.id,
                quantity=quantity,
                side=side,
                confidence=signal.confidence,
                regime=signal.market_assessment,
                balance_after=account.balance,
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar abertura groq: {e}")

        return trade

    async def _close_trade(
        self, session, trade: GroqTrade,
        exit_price: float, reason: str, thinking: str = "",
    ) -> None:
        """Fecha trade e calcula P&L com alavancagem."""
        side = trade.trade_side
        entry = trade.entry_price
        qty = trade.quantity
        lev = trade.leverage or LEVERAGE

        # PnL % (movimento do preço)
        if side == "LONG":
            pnl_pct = (exit_price - entry) / entry
        else:
            pnl_pct = (entry - exit_price) / entry

        pnl_pct_gross = round(pnl_pct * 100, 4)
        # PnL % com alavancagem
        pnl_pct_lev = round(pnl_pct_gross * lev, 4)
        fee_pct = round(FEE_TOTAL_PCT * 100 * lev, 4)  # Fees também escalam com leverage
        net_pnl_pct = round(pnl_pct_lev - fee_pct, 4)

        # PnL USD = quantidade × movimento × alavancagem
        price_move = abs(exit_price - entry)
        pnl_usd_gross = round(qty * price_move * lev * (1 if pnl_pct > 0 else -1), 6)
        fee_usd = round(entry * qty * lev * FEE_TOTAL_PCT, 6)
        pnl_usd_net = round(pnl_usd_gross - fee_usd, 6)

        # Atualizar trade
        trade.exit_price = exit_price
        trade.pnl = pnl_usd_net
        trade.pnl_pct = pnl_pct_lev
        trade.fee_cost_pct = fee_pct
        trade.net_pnl_pct = net_pnl_pct
        trade.status = "CLOSED"
        trade.close_reason = reason
        trade.closed_at = datetime.now(timezone.utc)
        trade.duration_minutes = round(
            (datetime.now(timezone.utc) - trade.opened_at.replace(tzinfo=timezone.utc)).total_seconds() / 60, 1
        )

        # Atualizar conta
        account = await self._get_or_create_account(session)
        account.balance = round(account.balance + pnl_usd_net, 6)
        account.total_pnl = round(account.total_pnl + pnl_usd_net, 6)
        if account.balance > account.peak_balance:
            account.peak_balance = account.balance
        if net_pnl_pct > 0:
            account.winning_trades += 1
        else:
            account.losing_trades += 1
        account.updated_at = datetime.now(timezone.utc)

        won = net_pnl_pct > 0
        outcome = "WIN" if won else "LOSS"

        logger.info(
            f"[Groq] FECHADO {side} {trade.symbol} @ ${exit_price:,.2f} "
            f"pnl={pnl_pct_lev:+.2f}% net={net_pnl_pct:+.2f}% motivo={reason} [{outcome}]"
        )

        # Risk manager
        groq_risk.record_trade(won)

        # Log de atividade
        try:
            await log_activity(
                agent="groq",
                event="close",
                symbol=trade.symbol,
                price=exit_price,
                trade_id=trade.id,
                quantity=qty,
                side=side,
                pnl=pnl_usd_net,
                pnl_pct=net_pnl_pct,
                reason=reason,
                regime=trade.regime_at_entry,
                balance_after=account.balance,
                extra={"thinking": thinking[:200], "gross_pnl_pct": pnl_pct_gross, "leverage": lev},
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar fechamento groq: {e}")

    async def _check_sl_tp(self, session, trade: GroqTrade, current_price: float) -> None:
        """Verifica se SL ou TP foram atingidos."""
        side = trade.trade_side

        # Stop Loss
        if side == "LONG" and current_price <= trade.stop_loss_price:
            await self._close_trade(session, trade, current_price, "STOP_LOSS")
            return
        if side == "SHORT" and current_price >= trade.stop_loss_price:
            await self._close_trade(session, trade, current_price, "STOP_LOSS")
            return

        # Take Profit
        if side == "LONG" and current_price >= trade.take_profit_price:
            await self._close_trade(session, trade, current_price, "TAKE_PROFIT")
            return
        if side == "SHORT" and current_price <= trade.take_profit_price:
            await self._close_trade(session, trade, current_price, "TAKE_PROFIT")
            return

    async def _check_time_stop(self, session, trade: GroqTrade, current_price: float) -> None:
        """Verifica time stop (4h)."""
        now = datetime.now(timezone.utc)
        opened = trade.opened_at.replace(tzinfo=timezone.utc) if trade.opened_at.tzinfo is None else trade.opened_at
        minutes = (now - opened).total_seconds() / 60
        if minutes >= MAX_TRADE_MINUTES:
            await self._close_trade(session, trade, current_price, "TIME_STOP")

    async def _save_thinking(self, signal: GroqSignalResult, symbol: str) -> None:
        """Salva o raciocínio do LLM no banco (inclui estratégia usada)."""
        try:
            thinking = GroqThinking(
                symbol=symbol,
                action=signal.action,
                confidence=signal.confidence,
                reasoning=f"[Estratégia: {signal.strategy_used}] {signal.reasoning}" if signal.strategy_used else signal.reasoning,
                raw_response=signal.raw_response,
                prompt_tokens=signal.prompt_tokens,
                output_tokens=signal.output_tokens,
                latency_ms=signal.latency_ms,
                error=signal.error if signal.error else None,
            )
            async with AsyncSessionLocal() as session:
                session.add(thinking)
                await session.commit()
        except Exception as e:
            logger.debug(f"[Groq] Falha ao salvar thinking: {e}")

    # ── Queries ──────────────────────────────────────────────────────────────

    async def _get_or_create_account(self, session) -> GroqAccount:
        acc = await session.scalar(select(GroqAccount))
        if acc is None:
            acc = GroqAccount(
                balance=INITIAL_BALANCE,
                initial_balance=INITIAL_BALANCE,
                peak_balance=INITIAL_BALANCE,
            )
            session.add(acc)
            await session.flush()
            await session.refresh(acc)
        return acc

    async def _get_open_trade(self, session, symbol: str) -> GroqTrade | None:
        return await session.scalar(
            select(GroqTrade).where(
                GroqTrade.symbol == symbol,
                GroqTrade.status == "OPEN",
            )
        )

    async def _get_recent_trades(self, session, symbol: str, limit: int = 5) -> list[dict]:
        result = await session.execute(
            select(GroqTrade).where(
                GroqTrade.symbol == symbol,
                GroqTrade.status == "CLOSED",
            ).order_by(desc(GroqTrade.closed_at)).limit(limit)
        )
        trades = result.scalars().all()
        return [
            {
                "side": t.trade_side,
                "symbol": t.symbol,
                "pnl_pct": t.net_pnl_pct,
                "close_reason": t.close_reason,
            }
            for t in trades
        ]

    # ── Public queries ──────────────────────────────────────────────────────

    async def get_account(self) -> GroqAccount | None:
        async with AsyncSessionLocal() as session:
            return await self._get_or_create_account(session)

    async def get_open_trades(self) -> list[GroqTrade]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GroqTrade).where(GroqTrade.status == "OPEN")
            )
            return list(result.scalars().all())

    async def get_recent_thinking(self, limit: int = 20) -> list[GroqThinking]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(GroqThinking).order_by(desc(GroqThinking.created_at)).limit(limit)
            )
            return list(result.scalars().all())

    async def get_stats(self, days: int = 30) -> dict:
        """Estatísticas completas do agente."""
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            account = await self._get_or_create_account(session)

            result = await session.execute(
                select(GroqTrade).where(
                    GroqTrade.status == "CLOSED",
                    GroqTrade.closed_at >= since,
                )
            )
            trades = list(result.scalars().all())

        if not trades:
            return {
                "total_trades": 0, "win_rate": 0, "profit_factor": 0,
                "total_pnl": 0, "total_pnl_pct": 0,
                "avg_win": 0, "avg_loss": 0, "max_drawdown": 0,
                "balance": account.balance,
                "net_win_rate": 0, "net_profit_factor": 0,
                "total_net_pnl_pct": 0,
            }

        wins = [t for t in trades if (t.net_pnl_pct or 0) > 0]
        losses = [t for t in trades if (t.net_pnl_pct or 0) <= 0]

        wr = len(wins) / len(trades) * 100
        gp = sum(t.net_pnl_pct or 0 for t in wins)
        gl = abs(sum(t.net_pnl_pct or 0 for t in losses))
        pf = gp / gl if gl > 0 else (float("inf") if gp > 0 else 0)

        total_pnl = sum(t.pnl or 0 for t in trades)
        total_net = sum(t.net_pnl_pct or 0 for t in trades)

        return {
            "total_trades": len(trades),
            "win_rate": round(wr, 1),
            "profit_factor": round(pf, 3),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(sum(t.pnl_pct or 0 for t in trades), 2),
            "avg_win": round(sum(t.net_pnl_pct or 0 for t in wins) / len(wins), 2) if wins else 0,
            "avg_loss": round(sum(t.net_pnl_pct or 0 for t in losses) / len(losses), 2) if losses else 0,
            "max_drawdown": 0,  # TODO: calcular
            "balance": account.balance,
            "net_win_rate": round(wr, 1),
            "net_profit_factor": round(pf, 3),
            "total_net_pnl_pct": round(total_net, 2),
            "consecutive_losses": groq_risk.consecutive_losses,
            "is_paused": groq_risk.is_paused,
        }


# Singleton
groq_engine = GroqTradeEngine()
