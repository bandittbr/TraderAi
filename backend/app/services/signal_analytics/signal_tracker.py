"""
Signal Tracker — Phase 6

Responsabilidades:
  1. record_signal()  — grava todo sinal emitido no banco (outcome=OPEN)
  2. resolve_signal() — atualiza outcome WIN/LOSS quando posição fecha
  3. resolve_timeout() — marca MISSED sinais OPEN com mais de MAX_OPEN_HOURS
  4. get_open_signals() — retorna sinais OPEN para monitorar preço
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.analytics import (
    SignalHistory, SignalDirection, SignalOutcome, MarketRegimeType,
)
from app.services.signal_analytics.regime_classifier import RegimeResult

logger = logging.getLogger(__name__)

# Sinal OPEN por mais de N horas é marcado MISSED
MAX_OPEN_HOURS = 48


# ─────────────────────────────────────────────
# Mapeamentos
# ─────────────────────────────────────────────

def _map_signal_direction(signal: str) -> SignalDirection:
    mapping = {
        "BUY":     SignalDirection.BUY,
        "SELL":    SignalDirection.SELL,
        "NEUTRAL": SignalDirection.NEUTRAL,
    }
    return mapping.get(signal.upper(), SignalDirection.NEUTRAL)


def _map_regime(regime_type: Optional[MarketRegimeType]) -> MarketRegimeType:
    if regime_type is None:
        return MarketRegimeType.UNKNOWN
    return regime_type


# ─────────────────────────────────────────────
# Signal Tracker
# ─────────────────────────────────────────────

class SignalTracker:
    """
    Persiste e resolve sinais históricos de forma assíncrona.
    Todos os métodos abrem sua própria sessão — thread-safe.
    """

    async def record_signal(
        self,
        *,
        symbol:        str,
        timeframe:     str,
        signal:        str,           # "BUY" | "SELL" | "NEUTRAL"
        confidence:    float,
        indicator:     Any,           # objeto com atributos técnicos
        current_price: float,
        regime:        Optional[RegimeResult]     = None,
        context:       Any                        = None,  # ContextScore or None
        criteria_met:  Optional[list[str]]        = None,
        context_boost: int                        = 0,
        trade_side:    Optional[str]              = None,  # LONG | SHORT (auto-derived)
        smc:           Any                        = None,  # SmartMoneyResult | None (Phase 7)
        structure:     Any                        = None,  # MarketStructureResult | None (Phase 6.5)
        raw_score:     Optional[float]            = None,  # Phase 8 V6
        weighted_score:Optional[float]            = None,  # Phase 8 V6
        weights_version: Optional[int]            = None,  # Phase 8 V6
    ) -> Optional[int]:
        """
        Grava um sinal no banco. Retorna o ID criado, ou None em caso de erro.
        """
        try:
            reg_type = _map_regime(regime.regime if regime else None)

            # Critérios atendidos → JSON
            criteria_json: Optional[str] = None
            if criteria_met:
                criteria_json = json.dumps(criteria_met)

            # Deriva trade_side automaticamente se não fornecido
            if trade_side is None:
                trade_side = "LONG" if signal.upper() != "SELL" else "SHORT"

            record = SignalHistory(
                symbol             = symbol,
                timeframe          = timeframe,
                signal             = _map_signal_direction(signal),
                confidence         = round(confidence, 2),
                regime             = reg_type,
                trade_side         = trade_side,
                # Indicadores técnicos
                rsi                = _safe_float(indicator, "rsi"),
                ema_9              = _safe_float(indicator, "ema_9"),
                ema_21             = _safe_float(indicator, "ema_21"),
                ema_50             = _safe_float(indicator, "ema_50"),
                ema_200            = _safe_float(indicator, "ema_200"),
                macd               = _safe_float(indicator, "macd"),
                macd_signal        = _safe_float(indicator, "macd_signal"),
                macd_histogram     = _safe_float(indicator, "macd_histogram"),
                atr                = _safe_float(indicator, "atr"),
                price_at_emission  = round(current_price, 8),
                ema_alignment      = _build_ema_alignment(indicator),
                criteria_met       = criteria_json,
                criteria_count     = len(criteria_met) if criteria_met else None,
                context_boost      = context_boost,
                # Contexto de mercado
                news_score         = _safe_attr(context, "news_score"),
                news_sentiment     = _safe_attr(context, "news_sentiment"),
                fear_greed_value   = _safe_attr(context, "fear_greed"),
                fear_greed_label   = _safe_attr(context, "fear_greed_label"),
                funding_label      = _safe_attr(context, "funding_label"),
                context_score      = _safe_attr(context, "context_score"),
                # Smart Money Context — Phase 7
                had_sweep         = bool(getattr(smc, "has_recent_buy_sweep", False) or getattr(smc, "has_recent_sell_sweep", False)) if smc else None,
                had_fvg           = bool(getattr(smc, "has_bullish_fvg", False) or getattr(smc, "has_bearish_fvg", False)) if smc else None,
                had_hvn           = bool(getattr(smc, "near_hvn", False)) if smc else None,
                had_lvn           = bool(getattr(smc, "near_lvn", False)) if smc else None,
                liquidity_score   = float(getattr(smc, "liquidity_score", 50.0)) if smc else None,
                liquidity_label   = getattr(smc, "liquidity_label", None) if smc else None,
                sweep_type        = getattr(smc, "last_sweep_type", None) if smc else None,
                market_structure  = getattr(structure, "structure_label", None) if structure else None,
                # Phase 8 V6
                raw_score         = raw_score,
                weighted_score    = weighted_score,
                weights_version   = weights_version,
                # Resultado inicial
                outcome            = SignalOutcome.OPEN,
                emitted_at         = datetime.utcnow(),
            )

            async with AsyncSessionLocal() as db:
                db.add(record)
                await db.commit()
                await db.refresh(record)
                return record.id

        except Exception as exc:
            logger.error("signal_tracker.record_signal falhou: %s", exc)
            return None

    async def resolve_signal(
        self,
        signal_id:     int,
        *,
        entry_price:   float,
        exit_price:    float,
        exit_reason:   str,           # "TP" | "SL" | "MANUAL" | "TIMEOUT"
        duration_min:  int,
        trade_side:    str            = "LONG",  # LONG | SHORT
        max_fav_pct:   Optional[float] = None,
        max_adv_pct:   Optional[float] = None,
    ) -> None:
        """
        Resolve um sinal OPEN após fechamento de posição.
        Calcula pnl_pct corretamente para LONG e SHORT.
        """
        if entry_price <= 0:
            return

        if trade_side == "SHORT":
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100.0
        else:
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
        outcome = SignalOutcome.WIN if pnl_pct > 0 else SignalOutcome.LOSS

        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(SignalHistory)
                    .where(SignalHistory.id == signal_id)
                    .values(
                        outcome            = outcome,
                        entry_price        = round(entry_price, 8),
                        exit_price         = round(exit_price, 8),
                        pnl_pct            = round(pnl_pct, 4),
                        max_favorable_pct  = max_fav_pct,
                        max_adverse_pct    = max_adv_pct,
                        trade_duration_min = duration_min,
                        exit_reason        = exit_reason,
                        resolved_at        = datetime.utcnow(),
                    )
                )
                await db.commit()
        except Exception as exc:
            logger.error("signal_tracker.resolve_signal(%d) falhou: %s", signal_id, exc)

    async def mark_missed(self, signal_id: int) -> None:
        """Marca um sinal como MISSED (emitido mas sem posição aberta)."""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(SignalHistory)
                    .where(SignalHistory.id == signal_id)
                    .values(outcome=SignalOutcome.MISSED, resolved_at=datetime.utcnow())
                )
                await db.commit()
        except Exception as exc:
            logger.error("signal_tracker.mark_missed(%d) falhou: %s", signal_id, exc)

    async def expire_old_open_signals(self) -> int:
        """
        Marca MISSED todos os sinais OPEN mais velhos que MAX_OPEN_HOURS.
        Retorna quantidade de registros atualizados.
        """
        cutoff = datetime.utcnow() - timedelta(hours=MAX_OPEN_HOURS)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    update(SignalHistory)
                    .where(
                        and_(
                            SignalHistory.outcome   == SignalOutcome.OPEN,
                            SignalHistory.emitted_at < cutoff,
                        )
                    )
                    .values(outcome=SignalOutcome.MISSED, resolved_at=datetime.utcnow())
                )
                await db.commit()
                return result.rowcount or 0
        except Exception as exc:
            logger.error("signal_tracker.expire_old_open_signals falhou: %s", exc)
            return 0

    async def resolve_most_recent_open(
        self,
        *,
        symbol:       str,
        trade_side:   str,    # LONG | SHORT
        entry_price:  float,
        exit_price:   float,
        exit_reason:  str,
        duration_min: int,
    ) -> bool:
        """
        Localiza o sinal OPEN mais recente para (symbol, trade_side)
        e o resolve. Retorna True se encontrou e resolveu.
        Chamado pelo TradeEngine ao fechar um paper trade.
        """
        sig_dir = "BUY" if trade_side == "LONG" else "SELL"
        direction_enum = _map_signal_direction(sig_dir)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SignalHistory)
                    .where(
                        and_(
                            SignalHistory.symbol  == symbol,
                            SignalHistory.signal  == direction_enum,
                            SignalHistory.outcome == SignalOutcome.OPEN,
                        )
                    )
                    .order_by(SignalHistory.emitted_at.desc())
                    .limit(1)
                )
                record = result.scalar_one_or_none()

            if record is None:
                return False

            await self.resolve_signal(
                record.id,
                entry_price  = entry_price,
                exit_price   = exit_price,
                exit_reason  = exit_reason,
                duration_min = duration_min,
                trade_side   = trade_side,
            )
            return True
        except Exception as exc:
            logger.error("signal_tracker.resolve_most_recent_open falhou: %s", exc)
            return False

    async def get_open_signals(self, symbol: Optional[str] = None) -> list[SignalHistory]:
        """Retorna sinais ainda OPEN para monitoramento de preço."""
        try:
            async with AsyncSessionLocal() as db:
                conditions = [SignalHistory.outcome == SignalOutcome.OPEN]
                if symbol:
                    conditions.append(SignalHistory.symbol == symbol)
                result = await db.execute(
                    select(SignalHistory).where(and_(*conditions))
                )
                return list(result.scalars().all())
        except Exception as exc:
            logger.error("signal_tracker.get_open_signals falhou: %s", exc)
            return []


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _safe_float(obj: Any, attr: str) -> Optional[float]:
    val = getattr(obj, attr, None)
    if val is None:
        return None
    try:
        return round(float(val), 8)
    except (TypeError, ValueError):
        return None


def _safe_attr(obj: Any, attr: str) -> Any:
    if obj is None:
        return None
    return getattr(obj, attr, None)


def _build_ema_alignment(indicator: Any) -> str:
    """Retorna string legível da ordenação EMA. Ex: '9>21>50>200'"""
    emas = {
        "9":   _safe_float(indicator, "ema_9")   or 0.0,
        "21":  _safe_float(indicator, "ema_21")  or 0.0,
        "50":  _safe_float(indicator, "ema_50")  or 0.0,
        "200": _safe_float(indicator, "ema_200") or 0.0,
    }
    sorted_emas = sorted(emas.items(), key=lambda x: x[1], reverse=True)
    return ">".join(label for label, _ in sorted_emas)


# ─────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────

signal_tracker = SignalTracker()
