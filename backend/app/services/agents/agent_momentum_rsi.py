"""
Agente 1: Momentum/RSI Reversal
Estratégia: SMA7/SMA25 + RSI para reversão
- Tendência: SMA7 < SMA25 = baixista, SMA7 > SMA25 = altista
- RSI < 30 = oversold → LONG, RSI > 70 = overbought → SHORT
- SL a -1.5% do capital global, TP Ratio 1:2
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class MomentumRSIAgent(BaseAgent):
    """
    Agente Momentum/RSI.
    Opera reversão baseada em SMA7/SMA25 + RSI.
    """

    def __init__(self):
        super().__init__(
            name="Momentum RSI",
            description="SMA7/SMA25 + RSI para reversão. Compra oversold, vende overbought.",
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

        # Usa timeframe 1h para análise principal
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

        # Extrair indicadores
        rsi = getattr(ind, "rsi", 50) or 50
        e7 = getattr(ind, "ema_9", None) or getattr(ind, "ema_7", None)
        e25 = getattr(ind, "ema_21", None) or getattr(ind, "ema_25", None)
        atr = getattr(ind, "atr", None)

        # Calcular ATR%
        atr_pct = 0.01
        if atr and price > 0:
            atr_pct = atr / price

        # Lógica de sinal
        direction = AgentSide.NEUTRAL
        confidence = 0.0
        reason_parts = []
        score = 50.0

        # SMA alignment
        if e7 is not None and e25 is not None:
            if e7 > e25:
                reason_parts.append("SMA7>SMA25 altista")
                score += 10
            elif e7 < e25:
                reason_parts.append("SMA7<SMA25 baixista")
                score -= 10

        # RSI reversal
        if rsi < 30:
            score += 25
            reason_parts.append(f"RSI oversold ({rsi:.0f})")
        elif rsi > 70:
            score -= 25
            reason_parts.append(f"RSI overbought ({rsi:.0f})")
        elif 30 <= rsi <= 40:
            score += 10
            reason_parts.append(f"RSI baixo ({rsi:.0f})")
        elif 60 <= rsi <= 70:
            score -= 10
            reason_parts.append(f"RSI alto ({rsi:.0f})")

        # Regime alignment
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str in ("BULL", "HIGH_VOLATILITY"):
                score += 5
            elif regime_str == "BEAR":
                score -= 5

        # Decisão
        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)
        else:
            direction = AgentSide.NEUTRAL
            confidence = 0

        # SL/TP
        sl_pct = max(0.005, atr_pct * 1.5)
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp_price = None
        tp2_price = None
        tp3_price = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            rr = 2.0  # TP Ratio 1:2
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp_price = price + sl_dist * rr
                tp2_price = price + sl_dist * 3.0
                tp3_price = price + sl_dist * 5.0
            else:
                sl_dist = sl_price - price
                tp_price = price - sl_dist * rr
                tp2_price = price - sl_dist * 3.0
                tp3_price = price - sl_dist * 5.0

            if confidence >= 80:
                lev = 2
            elif confidence >= 70:
                lev = 1

        reason = " | ".join(reason_parts) if reason_parts else "neutro"

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp_price, 8) if tp_price else None,
            take_profit2=round(tp2_price, 8) if tp2_price else None,
            take_profit3=round(tp3_price, 8) if tp3_price else None,
            leverage=lev, reason=reason,
            regime=str(regime_label) if regime_label else "UNKNOWN",
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={"rsi": rsi, "score": score},
        )
