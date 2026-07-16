"""
Agente 6: Grid Scalper
Estratégia: Trades de alta frequência com stops apertados
- Usa timeframe 15m para entrada
- Stops apertados (0.3-0.5%)
- TP rápido (R:R 1.0-1.5)
- Muitas entradas com stops pequenos
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class GridScalperAgent(BaseAgent):
    """
    Agente Grid Scalper.
    Trades de alta frequência com stops apertados.
    """

    def __init__(self):
        super().__init__(
            name="Grid Scalper",
            description="Trades de alta frequência com stops apertados (0.3-0.5%) e TP rápido.",
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

        # Grid Scalper usa 15m prioritariamente
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

        atr = getattr(ind, "atr", None)
        atr_pct = (atr / price) if atr and price > 0 else 0.01

        # Só opera em volatilidade moderada
        if atr_pct > 0.03:
            return AgentResult(
                agent_name=self.name, symbol=symbol,
                signal=AgentSignal(
                    agent_name=self.name, symbol=symbol,
                    direction=AgentSide.NEUTRAL, confidence=0,
                    entry_price=price, stop_loss=0,
                    reason=f"ATR muito alto para scalper: {atr_pct*100:.2f}%",
                    is_valid=False, atr_pct=atr_pct,
                ),
                error="ATR too high for scalping",
            )

        # Sinais rápidos no 15m
        rsi = getattr(ind, "rsi", 50) or 50
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)

        score = 50.0
        reason_parts = []

        # RSI para scalping
        if rsi < 35:
            score += 20
            reason_parts.append(f"RSI oversold ({rsi:.0f})")
        elif rsi > 65:
            score -= 20
            reason_parts.append(f"RSI overbought ({rsi:.0f})")
        elif 45 <= rsi <= 55:
            score += 5
            reason_parts.append(f"RSI neutro ({rsi:.0f})")

        # MACD rápido
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                score += 15
                reason_parts.append("MACD altista")
            elif macd < macd_sig:
                score -= 15
                reason_parts.append("MACD baixista")

        # EMA curta
        if e9 is not None and e21 is not None:
            if e9 > e21:
                score += 10
            elif e9 < e21:
                score -= 10

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # Stops apertados para scalper
        sl_pct = max(0.003, atr_pct * 1.0)  # 0.3-1.0%
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp_price = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            rr = 1.5  # R:R baixo para scalper
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
            regime=str(getattr(getattr(regime, "regime", None), "name", "UNKNOWN")),
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={"score": score},
        )
