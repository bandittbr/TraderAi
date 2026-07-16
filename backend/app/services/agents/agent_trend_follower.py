"""
Agente 8: Trend Follower
Estratégia: Segue a tendência com trailing stop
- EMA alignment para direção
- Entra na direção da EMA9/EMA21/EMA50 alinhadas
- Trailing stop progressivo
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class TrendFollowerAgent(BaseAgent):
    """
    Agente Trend Follower.
    Segue a tendência com EMA alignment e trailing stop.
    """

    def __init__(self):
        super().__init__(
            name="Trend Follower",
            description="Segue EMA alignment com trailing stop progressivo.",
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

        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)
        e50 = getattr(ind, "ema_50", None)
        e200 = getattr(ind, "ema_200", None)
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)

        score = 50.0
        reason_parts = []

        # EMA alignment (peso principal)
        if all(v is not None for v in [e9, e21, e50]):
            if e9 > e21 > e50:
                score += 30
                reason_parts.append("EMA bull perfeito")
                if e200 is not None and e50 > e200:
                    score += 10
                    reason_parts.append("EMA200 confirmada")
            elif e9 < e21 < e50:
                score -= 30
                reason_parts.append("EMA bear perfeito")
                if e200 is not None and e50 < e200:
                    score -= 10
                    reason_parts.append("EMA200 confirmada")
            elif e9 > e21:
                score += 10
                reason_parts.append("EMA bull parcial")
            elif e9 < e21:
                score -= 10
                reason_parts.append("EMA bear parcial")

        # MACD confirmation
        if macd is not None and macd_sig is not None:
            if macd > macd_sig and macd > 0:
                score += 15
                reason_parts.append("MACD altista")
            elif macd < macd_sig and macd < 0:
                score -= 15
                reason_parts.append("MACD baixista")

        # Structure confirmation
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "HH" in struct_label and "HL" in struct_label:
                score += 10
                reason_parts.append("Estrutura altista")
            elif "LH" in struct_label and "LL" in struct_label:
                score -= 10
                reason_parts.append("Estrutura baixista")

        # Regime
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str == "BULL":
                score += 5
            elif regime_str == "BEAR":
                score -= 5

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # SL baseado em ATR (mais largo para trend)
        sl_pct = max(0.01, atr_pct * 2.0)
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp1 = tp2 = tp3 = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp1 = price + sl_dist * 2.0
                tp2 = price + sl_dist * 4.0
                tp3 = price + sl_dist * 6.0
            else:
                sl_dist = sl_price - price
                tp1 = price - sl_dist * 2.0
                tp2 = price - sl_dist * 4.0
                tp3 = price - sl_dist * 6.0

            if confidence >= 80:
                lev = 2

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp1, 8) if tp1 else None,
            take_profit2=round(tp2, 8) if tp2 else None,
            take_profit3=round(tp3, 8) if tp3 else None,
            leverage=lev,
            reason=" | ".join(reason_parts) if reason_parts else "neutro",
            regime=str(regime_label) if regime_label else "UNKNOWN",
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={"score": score},
        )
