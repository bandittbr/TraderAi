"""
Agente 10: Breakout Trader
Estratégia: Opera rompimentos de suporte/resistência
- Identifica níveis chave (suporte/resistência)
- Entra no rompimento com volume
- SL abaixo do nível rompido
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class BreakoutAgent(BaseAgent):
    """
    Agente Breakout Trader.
    Opera rompimentos de suporte/resistência.
    """

    def __init__(self):
        super().__init__(
            name="Breakout",
            description="Opera rompimentos de suporte/resistência com confirmação de estrutura.",
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

        score = 50.0
        reason_parts = []

        # Structure-based breakout detection
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "CH" in struct_label:  # Change of character = breakout
                score += 30
                reason_parts.append(f"Change of character ({struct_label})")
            elif "HH" in struct_label and "HL" in struct_label:
                score += 15
                reason_parts.append("Estrutura altista")
            elif "LH" in struct_label and "LL" in struct_label:
                score -= 15
                reason_parts.append("Estrutura baixista")

        # SMC confirmation
        if smc:
            fvg_bull = getattr(smc, "has_bullish_fvg", False)
            fvg_bear = getattr(smc, "has_bearish_fvg", False)
            sweep_sell = getattr(smc, "has_recent_sell_sweep", False)
            sweep_buy = getattr(smc, "has_recent_buy_sweep", False)

            if fvg_bull:
                score += 10
                reason_parts.append("FVG altista")
            if fvg_bear:
                score -= 10
                reason_parts.append("FVG baixista")
            if sweep_sell:
                score += 8
                reason_parts.append("Sell sweep")
            if sweep_buy:
                score -= 8
                reason_parts.append("Buy sweep")

        # EMA momentum
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)
        if e9 is not None and e21 is not None:
            if e9 > e21:
                score += 10
                reason_parts.append("EMA momentum altista")
            elif e9 < e21:
                score -= 10
                reason_parts.append("EMA momentum baixista")

        # MACD
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                score += 10
            elif macd < macd_sig:
                score -= 10

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # SL abaixo do breakout
        sl_pct = max(0.008, atr_pct * 1.5)
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp1 = tp2 = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp1 = price + sl_dist * 2.0
                tp2 = price + sl_dist * 4.0
            else:
                sl_dist = sl_price - price
                tp1 = price - sl_dist * 2.0
                tp2 = price - sl_dist * 4.0

            if confidence >= 80:
                lev = 2

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp1, 8) if tp1 else None,
            take_profit2=round(tp2, 8) if tp2 else None,
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
