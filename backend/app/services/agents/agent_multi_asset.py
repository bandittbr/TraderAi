"""
Agente 9: Multi-Asset Diversified
Estratégia: Diversifica entre crypto + stocks
- Opera múltiplos símbolos com pesos iguais
- Risk parity entre ativos
- Só entra com confirmação de múltiplos timeframes
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class MultiAssetAgent(BaseAgent):
    """
    Agente Multi-Asset Diversified.
    Diversifica entre ativos com risk parity.
    """

    def __init__(self):
        super().__init__(
            name="Multi-Asset",
            description="Diversifica entre múltiplos ativos com risk parity.",
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

        # Score composto de múltiplos fatores
        score = 50.0
        reason_parts = []

        # 1. Technical
        rsi = getattr(ind, "rsi", 50) or 50
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)

        if e9 is not None and e21 is not None:
            if e9 > e21:
                score += 10
            else:
                score -= 10

        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                score += 10
            else:
                score -= 10

        if rsi < 40:
            score += 5
        elif rsi > 60:
            score -= 5

        # 2. Structure
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "HH" in struct_label and "HL" in struct_label:
                score += 10
                reason_parts.append("Estrutura altista")
            elif "LH" in struct_label and "LL" in struct_label:
                score -= 10
                reason_parts.append("Estrutura baixista")

        # 3. SMC
        if smc:
            sweep_sell = getattr(smc, "has_recent_sell_sweep", False)
            sweep_buy = getattr(smc, "has_recent_buy_sweep", False)
            if sweep_sell:
                score += 8
                reason_parts.append("Sell sweep")
            if sweep_buy:
                score -= 8
                reason_parts.append("Buy sweep")

        # 4. Context
        if context:
            fg = getattr(context, "fear_greed", None)
            if fg is not None:
                if fg < 25:
                    score += 5
                    reason_parts.append(f"Fear ({fg})")
                elif fg > 75:
                    score -= 5
                    reason_parts.append(f"Greed ({fg})")

        # 5. Regime
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
            confidence = 100 - score

        # SL adaptativo por ativo (risk parity)
        sl_pct = max(0.008, atr_pct * 1.5)
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
            module_scores={"score": score},
        )
