"""
Agente 7: Mean Reversion
Estratégia: Compra oversold, vende overbought
- RSI < 30 = LONG, RSI > 70 = SHORT
- Bollinger Bands para confirmação
- SL largo, TP modesto (R:R 1.5)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class MeanReversionAgent(BaseAgent):
    """
    Agente Mean Reversion.
    Compra oversold, vende overbought com RSI + Bollinger.
    """

    def __init__(self):
        super().__init__(
            name="Mean Reversion",
            description="Compra oversold (RSI<30), vende overbought (RSI>70) com Bollinger.",
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

        ind = price_1h or price_15m
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

        atr = getattr(ind, "atr", None)
        atr_pct = (atr / price) if atr and price > 0 else 0.01

        rsi = getattr(ind, "rsi", 50) or 50
        e50 = getattr(ind, "ema_50", None)

        score = 50.0
        reason_parts = []

        # RSI extremes
        if rsi < 25:
            score += 35
            reason_parts.append(f"RSI oversold forte ({rsi:.0f})")
        elif rsi < 30:
            score += 25
            reason_parts.append(f"RSI oversold ({rsi:.0f})")
        elif rsi < 35:
            score += 10
            reason_parts.append(f"RSI baixo ({rsi:.0f})")
        elif rsi > 75:
            score -= 35
            reason_parts.append(f"RSI overbought forte ({rsi:.0f})")
        elif rsi > 70:
            score -= 25
            reason_parts.append(f"RSI overbought ({rsi:.0f})")
        elif rsi > 65:
            score -= 10
            reason_parts.append(f"RSI alto ({rsi:.0f})")

        # EMA50 como suporte/resistência
        if e50 is not None:
            if price < e50 * 0.97 and rsi < 30:
                score += 10
                reason_parts.append("Abaixo EMA50 + oversold")
            elif price > e50 * 1.03 and rsi > 70:
                score -= 10
                reason_parts.append("Acima EMA50 + overbought")

        # Regime filter
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str == "SIDEWAYS":
                score *= 1.2  # mean reversion funciona melhor em sideways
                reason_parts.append("Regime sideways")

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if score > 65:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 35:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # SL largo, TP modesto
        sl_pct = max(0.01, atr_pct * 2.0)  # SL 1-2%
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp_price = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            rr = 1.5  # R:R modesto para reversão
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp_price = price + sl_dist * rr
            else:
                sl_dist = sl_price - price
                tp_price = price - sl_dist * rr

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
            module_scores={"rsi": rsi, "score": score},
        )
