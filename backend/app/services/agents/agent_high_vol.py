"""
Agente 2: High Vol Continuation
Estratégia: Opera em pares com alta volatilidade (ATR > 0.5%)
- Só entra se ATR% >= 0.5%
- Segue a tendência dominante (EMA alignment)
- Usa timeframe 15m para entrada
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)

MIN_ATR_PCT = 0.005  # 0.5%


class HighVolContinuationAgent(BaseAgent):
    """
    Agente High Vol Continuation.
    Opera continuation em pares com alta volatilidade.
    """

    def __init__(self):
        super().__init__(
            name="High Vol Continuation",
            description="Opera continuation em pares com ATR > 0.5%. Segue EMA alignment.",
        )

    async def analyze(
        self,
        symbol:      str,
        price_1h:    Optional[Any],
        price_15m:   Optional[Any],
        regime:      Optional[Any] = None,
        context:     Optional[Any] = None,
        structure:   Optional[Any] = None,
        smc:         Optional[Any] = None,
        current_price: Optional[float] = None,
        **kwargs,
    ) -> AgentResult:
        start = datetime.now(timezone.utc)
        self._last_execution = start

        ind = price_15m or price_1h
        if ind is None:
            return AgentResult(
                agent_name=self.name, symbol=symbol,
                signal=AgentSignal(
                    agent_name=self.name, symbol=symbol,
                    direction=AgentSide.NEUTRAL, confidence=0,
                    entry_price=0, stop_loss=0, reason="Sem dados",
                    is_valid=False,
                ),
                error="No indicator data",
            )

        price = current_price or getattr(ind, "close", None) or getattr(ind, "price", None) or 0.0
        if price <= 0:
            return AgentResult(
                agent_name=self.name, symbol=symbol,
                signal=AgentSignal(
                    agent_name=self.name, symbol=symbol,
                    direction=AgentSide.NEUTRAL, confidence=0,
                    entry_price=0, stop_loss=0, reason="Preço inválido",
                    is_valid=False,
                ),
                error="Invalid price",
            )

        # Extrair indicadores
        atr = getattr(ind, "atr", None)
        atr_pct = (atr / price) if atr and price > 0 else 0.01

        # Filtro de volatilidade
        if atr_pct < MIN_ATR_PCT:
            return AgentResult(
                agent_name=self.name, symbol=symbol,
                signal=AgentSignal(
                    agent_name=self.name, symbol=symbol,
                    direction=AgentSide.NEUTRAL, confidence=0,
                    entry_price=price, stop_loss=0,
                    reason=f"ATR muito baixo: {atr_pct*100:.3f}% < {MIN_ATR_PCT*100:.1f}%",
                    is_valid=False, atr_pct=atr_pct,
                ),
                error=f"ATR too low: {atr_pct*100:.3f}%",
            )

        # EMA alignment para direção
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)
        e50 = getattr(ind, "ema_50", None)

        direction = AgentSide.NEUTRAL
        confidence = 0.0
        score = 50.0
        reason_parts = [f"ATR={atr_pct*100:.2f}%"]

        if all(v is not None for v in [e9, e21]):
            if e9 > e21:
                score += 20
                reason_parts.append("EMA9>EMA21 altista")
                if e50 is not None and e21 > e50:
                    score += 10
                    reason_parts.append("EMA alinhada")
            elif e9 < e21:
                score -= 20
                reason_parts.append("EMA9<EMA21 baixista")
                if e50 is not None and e21 < e50:
                    score -= 10
                    reason_parts.append("EMA alinhada")

        # MACD confirmation
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                score += 10
                reason_parts.append("MACD altista")
            elif macd < macd_sig:
                score -= 10
                reason_parts.append("MACD baixista")

        # Regime
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str == "HIGH_VOLATILITY":
                score += 10
                reason_parts.append("Alta volatilidade")

        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # SL/TP
        sl_pct = max(0.005, atr_pct * 1.2)
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp_price = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            rr = 2.0
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp_price = price + sl_dist * rr
            else:
                sl_dist = sl_price - price
                tp_price = price - sl_dist * rr

            if confidence >= 75:
                lev = 2

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp_price, 8) if tp_price else None,
            leverage=lev,
            reason=" | ".join(reason_parts) if reason_parts else "neutro",
            regime=str(regime_label) if regime_label else "UNKNOWN",
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={"atr_pct": atr_pct, "score": score},
        )
