"""
TradeAI - Trade Engine V2 (Futures Completo)

Simulador de Futures com suporte a LONG e SHORT.

ABERTURA:
  LONG  — qualquer sinal BUY (sem threshold de confiança)
  SHORT — qualquer sinal SELL (sem threshold de confiança)

FECHAMENTO:
  LONG:
    Stop Loss  : price <= entry * (1 - SL%)
    Take Profit: price >= entry * (1 + TP%)
    Sinal SELL : qualquer SELL fecha o LONG
  SHORT:
    Stop Loss  : price >= entry * (1 + SL%)
    Take Profit: price <= entry * (1 - TP%)
    Sinal BUY  : qualquer BUY fecha o SHORT

PnL:
  LONG  = (exit_price - entry_price) * quantity
  SHORT = (entry_price - exit_price) * quantity

Quantidade:
  quantity = paper_risk_per_trade / entry_price
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.paper_trading import PaperAccount, PaperTrade, TradeStatus, TradeSide
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


# ── Tipos de entrada ──────────────────────────────────────────────────────────

@dataclass
class SignalInput:
    symbol:     str
    timeframe:  str
    signal:     str      # "BUY" | "SELL" | "NEUTRAL"
    confidence: float    # 0-100
    trend:      str      # mantido para retrocompatibilidade (nao mais usado)
    price:      float
    # Phase 12 — contexto para Exit Score e TradeManager
    context:   Optional[Any] = field(default=None)
    regime:    Optional[Any] = field(default=None)
    structure: Optional[Any] = field(default=None)
    smc:       Optional[Any] = field(default=None)


@dataclass
class TradeMetrics:
    total_trades:    int
    open_trades:     int
    closed_trades:   int
    long_trades:     int
    short_trades:    int
    win_rate:        float    # 0-100 % (gross)
    win_rate_long:   float
    win_rate_short:  float
    profit_factor:   float    # gross
    avg_gain:        float    # USD (gross)
    avg_loss:        float    # USD (gross)
    max_drawdown:    float    # %
    total_pnl:       float    # USD (gross)
    total_pnl_pct:   float    # % (gross)
    current_balance: float
    # V7.11 — Net (fee-ajustado)
    net_win_rate:    float    = 0.0
    net_profit_factor: float  = 0.0
    total_net_pnl_pct: float  = 0.0


# ── V7: Paper Risk Manager (Circuit Breaker por Regime) ────────────────────────
# Mesma lógica do scalper: 3 perdas consecutivas → sizing 50%, 5 → pausa
PAPER_REGIMES = ("BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY", "UNKNOWN")
PAPER_REGIME_REDUCE_AFTER  = 3
PAPER_REGIME_PAUSE_AFTER   = 5
PAPER_REGIME_REDUCE_FACTOR = 0.5


class PaperRiskManager:
    """
    V7: Circuit Breaker por regime para Paper Trading.
    Rastreia perdas consecutivas por regime em memória.
    Reset automático no próximo dia UTC.
    """
    _today_str: str = ""
    _regime_losses: dict[str, int] = None

    def __init__(self):
        self._reset()

    def _reset(self) -> None:
        from datetime import date
        self._today_str = date.today().isoformat()
        self._regime_losses = {r: 0 for r in PAPER_REGIMES}

    def _check_day(self) -> None:
        from datetime import date
        today = date.today().isoformat()
        if today != self._today_str:
            self._reset()

    def regime_sizing_multiplier(self, regime: str) -> float:
        """1.0 normal | 0.5 após 3 perdas | 0.0 se pausado."""
        self._check_day()
        losses = self._regime_losses.get(regime, 0)
        if losses >= PAPER_REGIME_PAUSE_AFTER:
            return 0.0
        if losses >= PAPER_REGIME_REDUCE_AFTER:
            return PAPER_REGIME_REDUCE_FACTOR
        return 1.0

    def is_regime_paused(self, regime: str) -> bool:
        self._check_day()
        return self._regime_losses.get(regime, 0) >= PAPER_REGIME_PAUSE_AFTER

    def record_trade(self, won: bool, regime: str = "UNKNOWN") -> None:
        """
        Registra resultado e atualiza contador do regime.
        Vitória reseta o contador do regime.
        """
        self._check_day()
        if regime not in self._regime_losses:
            regime = "UNKNOWN"
        if won:
            was_paused = self._regime_losses[regime] >= PAPER_REGIME_PAUSE_AFTER
            self._regime_losses[regime] = 0
            if was_paused:
                logger.info(f"[PaperRisk] Regime {regime} reativado após vitória.")
        else:
            self._regime_losses[regime] += 1
            los = self._regime_losses[regime]
            if los == PAPER_REGIME_REDUCE_AFTER:
                logger.info(f"[PaperRisk] Regime {regime}: {los} consecutivas → sizing 50%")
            if los >= PAPER_REGIME_PAUSE_AFTER:
                logger.info(f"[PaperRisk] Regime {regime}: {los} consecutivas → PAUSADO")


# Singleton do risk manager
paper_risk = PaperRiskManager()


# ── Trade Engine ──────────────────────────────────────────────────────────────

class TradeEngine:
    """Singleton que processa sinais e gerencia a conta virtual de futures."""

    # ── Contadores de diagnóstico (in-memory, resetados ao reiniciar) ─────────
    _signals_processed:               int = 0
    _signals_rejected_confidence:     int = 0
    _signals_rejected_existing_trade: int = 0
    _last_execution: Optional[datetime] = None

    # ── Conta ─────────────────────────────────────────────────────────────────

    async def _get_or_create_account(self, session) -> PaperAccount:
        result  = await session.execute(select(PaperAccount).limit(1))
        account = result.scalar_one_or_none()
        if account is None:
            account = PaperAccount(
                balance         = settings.paper_initial_balance,
                initial_balance = settings.paper_initial_balance,
            )
            session.add(account)
            await session.flush()
            logger.info(
                f"[TradeEngine] Conta futures criada — "
                f"saldo inicial: ${settings.paper_initial_balance:.2f}"
            )
        return account

    async def get_account(self) -> PaperAccount | None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(PaperAccount).limit(1))
            return result.scalar_one_or_none()

    # ── Processar sinal ───────────────────────────────────────────────────────

    async def process_signal(self, sig: SignalInput) -> None:
        """
        Ponto de entrada principal.
        Chamado pelo scheduler apos cada calculo de indicadores.
        """
        try:
            async with AsyncSessionLocal() as session:
                await self._get_or_create_account(session)
                await session.commit()

            async with AsyncSessionLocal() as session:
                open_trade = await self._get_open_trade(session, sig.symbol, sig.timeframe)

                # ── Contadores de diagnóstico ──────────────────────────────
                TradeEngine._signals_processed += 1
                TradeEngine._last_execution     = datetime.now(timezone.utc)

                if open_trade:
                    # Trade aberto: verifica fechamento
                    if self._should_open(sig):
                        # Sinal válido mas trade já existe — descartado
                        TradeEngine._signals_rejected_existing_trade += 1
                    await self._maybe_close_trade(session, open_trade, sig)
                elif self._should_open(sig):
                    # V7: verifica circuit breaker por regime
                    regime_label = self._resolve_regime_label(sig)
                    if paper_risk.is_regime_paused(regime_label):
                        logger.info(
                            f"[TradeEngine] {sig.symbol} {sig.signal} ignorado — "
                            f"regime {regime_label} PAUSADO"
                        )
                    else:
                        await self._open_trade(session, sig)
                else:
                    # NEUTRAL — sem ação
                    pass

                await session.commit()

        except Exception as exc:
            logger.error(f"[TradeEngine] Erro ao processar sinal {sig.symbol}: {exc}")

    # ── Regras de abertura ────────────────────────────────────────────────────

    def _should_open(self, sig: SignalInput) -> bool:
        """
        Abre em qualquer sinal BUY ou SELL — sem threshold de confiança.
        O signal engine ja filtra qualidade dos sinais upstream.
        """
        return sig.signal in ("BUY", "SELL")

    def _resolve_regime_label(self, sig: SignalInput) -> str:
        """Extrai label do regime do sinal."""
        regime_raw = getattr(sig, 'regime', None)
        if regime_raw is None:
            return "UNKNOWN"
        regime_obj = getattr(regime_raw, 'regime', regime_raw)
        if hasattr(regime_obj, 'value'):
            return regime_obj.value
        return str(regime_obj)

    def _get_side(self, sig: SignalInput) -> str:
        """BUY -> LONG, SELL -> SHORT."""
        return TradeSide.LONG.value if sig.signal == "BUY" else TradeSide.SHORT.value

    async def _open_trade(self, session, sig: SignalInput) -> None:
        """Abre novo trade LONG ou SHORT."""
        side = self._get_side(sig)

        # V7: quantidade escala com confiança + circuit breaker por regime
        confidence_scale = max(0.25, min(1.0, (sig.confidence or 50) / 100))
        regime_label     = self._resolve_regime_label(sig)
        regime_scale     = paper_risk.regime_sizing_multiplier(regime_label)
        risk_effective   = settings.paper_risk_per_trade * confidence_scale * regime_scale
        quantity = round(risk_effective / sig.price, 8)

        trade = PaperTrade(
            symbol      = sig.symbol,
            timeframe   = sig.timeframe,
            signal      = sig.signal,
            confidence  = sig.confidence,
            trade_side  = side,
            entry_price = sig.price,
            quantity    = quantity,
            status      = TradeStatus.OPEN.value,
        )
        session.add(trade)
        await session.flush()  # flush para obter o ID do trade

        logger.info(
            f"[TradeEngine] ABERTO  {sig.symbol} {side} @ {sig.price:.4f} "
            f"qty={quantity:.6f} risk=${risk_effective:.2f} conf={sig.confidence:.0f}%"
        )

        # Log de atividade + broadcast WebSocket
        try:
            from app.services.trade_activity import log_activity
            account_result = await session.execute(select(PaperAccount).limit(1))
            account = account_result.scalar_one_or_none()
            await log_activity(
                agent="paper",
                event="open",
                symbol=sig.symbol,
                price=sig.price,
                trade_id=trade.id,
                quantity=quantity,
                side=side,
                confidence=sig.confidence,
                regime=regime_label,
                balance_after=account.balance if account else None,
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar abertura: {e}")

    # ── Regras de fechamento ──────────────────────────────────────────────────

    async def _maybe_close_trade(
        self, session, trade: PaperTrade, sig: SignalInput
    ) -> None:
        """
        Phase 12: delega ao TradeManager (time stop, BE, trailing, partial TP,
        exit score, signal close). Sem alteração no Signal Engine.
        """
        from app.services.trade_management.trade_manager import trade_manager as tm
        close_reason, exit_score = await tm.evaluate(
            session    = session,
            trade      = trade,
            sig_price  = sig.price,
            sig_signal = sig.signal,
            context    = sig.context,
            regime     = sig.regime,
            structure  = sig.structure,
            smc        = sig.smc,
        )
        if close_reason:
            regime_label = self._resolve_regime_label(sig)
            await self._close_trade(
                session, trade, sig.price, close_reason,
                exit_score=exit_score, regime_label=regime_label,
            )

    async def _close_trade(
        self,
        session,
        trade:       PaperTrade,
        exit_price:  float,
        reason:      str,
        exit_score:  Optional[float] = None,
        regime_label: str = "UNKNOWN",
    ) -> None:
        """Fecha o trade, calcula PnL (LONG ou SHORT) e atualiza saldo."""
        side  = trade.trade_side
        entry = trade.entry_price
        # FIX: após Partial TP1 a quantidade restante é menor — usar a cheia
        # contava o lucro da parcial duas vezes no saldo.
        qty   = trade.quantity
        if getattr(trade, "tp1_hit", False) and getattr(trade, "remaining_quantity", None):
            qty = trade.remaining_quantity

        if side == TradeSide.LONG.value:
            pnl     = (exit_price - entry) * qty
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            # SHORT: lucro quando preco cai
            pnl     = (entry - exit_price) * qty
            pnl_pct = (entry - exit_price) / entry * 100

        # V7.11 — Fee & slippage: 0.06% taker + 0.02% slippage por perna, arredondado
        FEE_SLIPPAGE_TOTAL_PCT = 0.0008 * 2  # 0.08% entrada + 0.08% saída = 0.16%
        fee_cost = round(FEE_SLIPPAGE_TOTAL_PCT * 100, 4)  # em pontos percentuais

        pnl_pct_rounded = round(pnl_pct, 4)
        net_pnl_pct_val = round(pnl_pct_rounded - fee_cost, 4)
        # PnL USD líquido de taxas
        pnl_net = pnl - round(entry * qty * FEE_SLIPPAGE_TOTAL_PCT, 6)

        trade.exit_price         = exit_price
        trade.pnl                = round(pnl, 6)
        trade.pnl_percent        = pnl_pct_rounded
        trade.fee_cost_pct       = fee_cost
        trade.net_pnl_percent    = net_pnl_pct_val
        trade.close_reason       = reason
        trade.status             = TradeStatus.CLOSED.value
        trade.closed_at          = datetime.now(timezone.utc)
        trade.exit_score_at_close = exit_score  # Phase 12

        # Atualiza saldo (com fee-ajuste)
        result  = await session.execute(select(PaperAccount).limit(1))
        account = result.scalar_one_or_none()
        if account:
            account.balance    = round(account.balance + pnl_net, 6)
            account.updated_at = datetime.now(timezone.utc)

        outcome = "WIN" if net_pnl_pct_val > 0 else "LOSS"
        logger.info(
            f"[TradeEngine] FECHADO {trade.symbol} {side} @ {exit_price:.4f} "
            f"gross={pnl_pct:+.3f}% net={net_pnl_pct_val:+.3f}% "
            f"motivo={reason} [{outcome}]"
        )

        # Log de atividade + broadcast WebSocket
        try:
            from app.services.trade_activity import log_activity
            await log_activity(
                agent="paper",
                event="close",
                symbol=trade.symbol,
                price=exit_price,
                trade_id=trade.id,
                quantity=qty,
                side=side,
                pnl=round(pnl_net, 6),
                pnl_pct=net_pnl_pct_val,
                reason=reason,
                regime=regime_label,
                balance_after=account.balance if account else None,
                extra={"exit_score": exit_score, "gross_pnl_pct": pnl_pct_rounded},
            )
        except Exception as e:
            logger.debug(f"[TradeActivity] Falha ao logar fechamento: {e}")

        # V7.11: registra resultado no circuit breaker (net, fee-ajustado)
        paper_risk.record_trade(won=(net_pnl_pct_val > 0), regime=regime_label)

        # Resolve sinal correspondente no signal_history (Phase 6)
        try:
            from app.services.signal_analytics.signal_tracker import signal_tracker
            opened_at = getattr(trade, "opened_at", None)
            dur_min   = 0
            if opened_at:
                delta   = datetime.now(timezone.utc) - (
                    opened_at if opened_at.tzinfo else opened_at.replace(tzinfo=timezone.utc)
                )
                dur_min = max(1, int(delta.total_seconds() / 60))
            await signal_tracker.resolve_most_recent_open(
                symbol       = trade.symbol,
                trade_side   = side,
                entry_price  = entry,
                exit_price   = exit_price,
                exit_reason  = reason,
                duration_min = dur_min,
            )
        except Exception:
            pass

    # ── Consultas ─────────────────────────────────────────────────────────────

    async def _get_open_trade(
        self, session, symbol: str, timeframe: str
    ) -> PaperTrade | None:
        result = await session.execute(
            select(PaperTrade).where(
                PaperTrade.symbol    == symbol,
                PaperTrade.timeframe == timeframe,
                PaperTrade.status    == TradeStatus.OPEN.value,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_trades(self, limit: int = 100) -> list[PaperTrade]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PaperTrade)
                .order_by(PaperTrade.opened_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_open_trades(self) -> list[PaperTrade]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PaperTrade)
                .where(PaperTrade.status == TradeStatus.OPEN.value)
            )
            return list(result.scalars().all())

    # ── Metricas ──────────────────────────────────────────────────────────────

    async def get_metrics(self) -> TradeMetrics:
        """Calcula metricas completas de performance LONG+SHORT."""
        async with AsyncSessionLocal() as session:
            result     = await session.execute(select(PaperTrade))
            trades     = list(result.scalars().all())
            result_acc = await session.execute(select(PaperAccount).limit(1))
            account    = result_acc.scalar_one_or_none()

        initial = settings.paper_initial_balance
        balance = account.balance if account else initial

        closed   = [t for t in trades if t.status == TradeStatus.CLOSED.value]
        open_cnt = len([t for t in trades if t.status == TradeStatus.OPEN.value])

        longs  = [t for t in closed if (t.trade_side or TradeSide.LONG.value) == TradeSide.LONG.value]
        shorts = [t for t in closed if (t.trade_side or TradeSide.LONG.value) == TradeSide.SHORT.value]

        wins   = [t for t in closed if (t.pnl or 0) >= 0]
        losses = [t for t in closed if (t.pnl or 0) <  0]

        wins_long  = [t for t in longs  if (t.pnl or 0) >= 0]
        wins_short = [t for t in shorts if (t.pnl or 0) >= 0]

        win_rate       = (len(wins)       / len(closed) * 100) if closed else 0.0
        win_rate_long  = (len(wins_long)  / len(longs)  * 100) if longs  else 0.0
        win_rate_short = (len(wins_short) / len(shorts) * 100) if shorts else 0.0

        gross_profit  = sum(t.pnl for t in wins   if t.pnl)
        gross_loss    = abs(sum(t.pnl for t in losses if t.pnl))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (
            float("inf") if gross_profit > 0 else 0.0
        )

        avg_gain = (gross_profit / len(wins))   if wins   else 0.0
        avg_loss = (gross_loss   / len(losses)) if losses else 0.0

        total_pnl    = sum(t.pnl for t in closed if t.pnl)
        max_drawdown = self._calculate_max_drawdown(closed, initial)

        # V7.11 — Net metrics (fee-ajustado)
        _net_pnl = lambda t: (t.net_pnl_percent if t.net_pnl_percent is not None else t.pnl_percent or 0.0)
        net_wins   = [t for t in closed if _net_pnl(t) > 0]
        net_losses = [t for t in closed if _net_pnl(t) <= 0]
        net_wr = (len(net_wins) / len(closed) * 100) if closed else 0.0
        net_gp = sum(_net_pnl(t) for t in net_wins)
        net_gl = abs(sum(_net_pnl(t) for t in net_losses)) if net_losses else 0.0
        net_pf = (net_gp / net_gl) if net_gl > 0 else (float("inf") if net_gp > 0 else 0.0)
        total_net_pnl = sum(_net_pnl(t) for t in closed)

        return TradeMetrics(
            total_trades     = len(trades),
            open_trades      = open_cnt,
            closed_trades    = len(closed),
            long_trades      = len(longs),
            short_trades     = len(shorts),
            win_rate         = round(win_rate, 2),
            win_rate_long    = round(win_rate_long, 2),
            win_rate_short   = round(win_rate_short, 2),
            profit_factor    = round(profit_factor, 4),
            avg_gain         = round(avg_gain, 6),
            avg_loss         = round(avg_loss, 6),
            max_drawdown     = round(max_drawdown, 2),
            total_pnl        = round(total_pnl, 6),
            total_pnl_pct    = round((total_pnl / initial) * 100, 4) if initial else 0.0,
            current_balance  = round(balance, 4),
            # V7.11
            net_win_rate     = round(net_wr, 2),
            net_profit_factor= round(net_pf, 4),
            total_net_pnl_pct= round(total_net_pnl, 4),
        )

    def _calculate_max_drawdown(
        self, closed_trades: list, initial_balance: float
    ) -> float:
        if not closed_trades:
            return 0.0
        sorted_trades = sorted(closed_trades, key=lambda t: t.closed_at or datetime.min)
        balance = initial_balance
        peak    = initial_balance
        max_dd  = 0.0
        for t in sorted_trades:
            balance += (t.pnl or 0)
            if balance > peak:
                peak = balance
            dd = ((peak - balance) / peak * 100) if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        return max_dd


    async def get_debug_stats(self) -> dict:
        """Retorna métricas de diagnóstico completo do Paper Trading."""
        from sqlalchemy import func as sqlfunc, and_
        from app.models.analytics import SignalHistory

        now_utc = datetime.now(timezone.utc)

        async with AsyncSessionLocal() as session:
            # ── Trades ────────────────────────────────────────────────────────
            r_open = await session.execute(
                select(sqlfunc.count()).select_from(PaperTrade)
                .where(PaperTrade.status == TradeStatus.OPEN.value)
            )
            trades_open: int = r_open.scalar_one() or 0

            r_closed = await session.execute(
                select(sqlfunc.count()).select_from(PaperTrade)
                .where(PaperTrade.status == TradeStatus.CLOSED.value)
            )
            trades_closed: int = r_closed.scalar_one() or 0

            # Oldest open trade
            r_oldest = await session.execute(
                select(
                    PaperTrade.opened_at,
                    PaperTrade.symbol,
                    PaperTrade.entry_price,
                    PaperTrade.trade_side,
                )
                .where(PaperTrade.status == TradeStatus.OPEN.value)
                .order_by(PaperTrade.opened_at.asc())
                .limit(1)
            )
            oldest_row = r_oldest.first()
            oldest_open_trade_hours = 0.0
            oldest_open_info: dict = {}
            if oldest_row:
                opened_at = oldest_row[0]
                if opened_at:
                    opened_utc = (
                        opened_at if opened_at.tzinfo
                        else opened_at.replace(tzinfo=timezone.utc)
                    )
                    oldest_open_trade_hours = round(
                        (now_utc - opened_utc).total_seconds() / 3600, 2
                    )
                oldest_open_info = {
                    "symbol":      oldest_row[1],
                    "entry_price": oldest_row[2],
                    "side":        oldest_row[3],
                    "opened_at":   str(oldest_row[0]),
                }

            # ── signal_history ────────────────────────────────────────────────
            signals_in_db           = -1
            signals_low_conf_in_db  = -1
            signals_high_conf_in_db = -1
            signals_btc_sell_in_db  = -1
            try:
                r_total = await session.execute(
                    select(sqlfunc.count()).select_from(SignalHistory)
                )
                signals_in_db = r_total.scalar_one() or 0

                r_low = await session.execute(
                    select(sqlfunc.count()).select_from(SignalHistory)
                    .where(
                        and_(
                            SignalHistory.signal.in_(["BUY", "SELL"]),
                            SignalHistory.confidence < 62.0,
                        )
                    )
                )
                signals_low_conf_in_db = r_low.scalar_one() or 0

                r_high = await session.execute(
                    select(sqlfunc.count()).select_from(SignalHistory)
                    .where(
                        and_(
                            SignalHistory.signal.in_(["BUY", "SELL"]),
                            SignalHistory.confidence >= 62.0,
                        )
                    )
                )
                signals_high_conf_in_db = r_high.scalar_one() or 0

                r_btc_sell = await session.execute(
                    select(sqlfunc.count()).select_from(SignalHistory)
                    .where(
                        and_(
                            SignalHistory.symbol == "BTCUSDT",
                            SignalHistory.signal == "SELL",
                        )
                    )
                )
                signals_btc_sell_in_db = r_btc_sell.scalar_one() or 0
            except Exception:
                pass

        # ── TP/SL esperados para o trade aberto ───────────────────────────────
        tp_sl_info: dict = {}
        if oldest_open_info:
            ep   = oldest_open_info.get("entry_price") or 0.0
            side = oldest_open_info.get("side", "LONG")
            sl_pct = settings.paper_stop_loss_percent / 100
            tp_pct = settings.paper_take_profit_percent / 100
            if side == "LONG":
                tp_sl_info = {
                    "sl_price": round(ep * (1 - sl_pct), 2),
                    "tp_price": round(ep * (1 + tp_pct), 2),
                }
            else:
                tp_sl_info = {
                    "sl_price": round(ep * (1 + sl_pct), 2),
                    "tp_price": round(ep * (1 - tp_pct), 2),
                }

        return {
            # In-memory (desde último restart)
            "signals_processed_since_restart":               TradeEngine._signals_processed,
            "signals_rejected_confidence_since_restart":     TradeEngine._signals_rejected_confidence,
            "signals_rejected_existing_trade_since_restart": TradeEngine._signals_rejected_existing_trade,
            "trade_engine_last_execution":                   str(TradeEngine._last_execution) if TradeEngine._last_execution else None,
            # Trades
            "trades_open":              trades_open,
            "trades_closed":            trades_closed,
            "oldest_open_trade_hours":  oldest_open_trade_hours,
            "oldest_open_trade_info":   oldest_open_info,
            "expected_tp_sl":           tp_sl_info,
            # signal_history (DB)
            "signals_generated":                 signals_in_db,
            "signals_rejected_confidence":        signals_low_conf_in_db,
            "signals_high_confidence":            signals_high_conf_in_db,
            "signals_btc_sell_total":             signals_btc_sell_in_db,
            # Config
            "config": {
                "sl_pct":                   settings.paper_stop_loss_percent,
                "tp_pct":                   settings.paper_take_profit_percent,
                "min_confidence_to_open":   0.0,  # Sem limite — toda oportunidade é aproveitada
                "close_by_signal":          "any SELL closes LONG / any BUY closes SHORT (sem filtro de confidence)",
            },
            # Diagnóstico
            "diagnosis": {
                "trade_closes_by_sl":     f"price <= entry × {1 - settings.paper_stop_loss_percent/100:.3f}",
                "trade_closes_by_tp":     f"price >= entry × {1 + settings.paper_take_profit_percent/100:.3f}",
                "trade_closes_by_signal": "sig.signal == 'SELL' (qualquer confidence fecha LONG)",
                "gargalo_suspeito": (
                    "Se signal_btc_sell_total == 0 ou muito baixo: Signal Engine nunca gera SELL para BTC. "
                    "Se TP/SL nao atingidos: BTC nao moveu +-2/4% desde a entrada. "
                    "Phase 12 adicionou Time Stop (48h), Trailing, BE e Partial TP."
                ),
            },
        }


# Singleton
trade_engine = TradeEngine()
