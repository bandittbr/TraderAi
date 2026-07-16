"""
Agente 5: Portfolio Cycle Manager
Estratégia: Gerencia múltiplos ativos com TP/SL em cascata
- TP1 parcial (40%), TP2 parcial (30%), TP3 (30%)
- SL a -1.5% do capital global
- Rebalanceia entre ativos baseado em performance
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class PortfolioCycleAgent(BaseAgent):
    """
    Agente Portfolio Cycle Manager.
    TP/SL em cascata com rebalanceamento entre ativos.
    """

    def __init__(self):
        super().__init__(
            name="Portfolio Cycle",
            description="TP/SL em cascata com rebalanceamento entre múltiplos ativos.",
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

        # Score baseado em estrutura de mercado + contexto
        score = 50.0
        reason_parts = []

        # Structure
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "HH" in struct_label and "HL" in struct_label:
                score += 20
                reason_parts.append(f"Estrutura altista")
            elif "LH" in struct_label and "LL" in struct_label:
                score -= 20
                reason_parts.append(f"Estrutura baixista")

        # SMC
        if smc:
            sweep_sell = getattr(smc, "has_recent_sell_sweep", False)
            sweep_buy = getattr(smc, "has_recent_buy_sweep", False)
            fvg_bull = getattr(smc, "has_bullish_fvg", False)
            fvg_bear = getattr(smc, "has_bearish_fvg", False)

            if sweep_sell:
                score += 10
                reason_parts.append("Sell sweep")
            if sweep_buy:
                score -= 10
                reason_parts.append("Buy sweep")
            if fvg_bull:
                score += 8
                reason_parts.append("FVG altista")
            if fvg_bear:
                score -= 8
                reason_parts.append("FVG baixista")

        # Regime
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str == "BULL":
                score += 10
            elif regime_str == "BEAR":
                score -= 10

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if score > 60:
            direction = AgentSide.LONG
            confidence = min(100, score)
        elif score < 40:
            direction = AgentSide.SHORT
            confidence = min(100, 100 - score)

        # SL/TP em cascata (1.5% SL, TP1=1.5: TP2=3.0, TP3=5.0)
        sl_pct = 0.015  # 1.5% do capital global
        sl_price = price * (1 - sl_pct) if direction == AgentSide.LONG else price * (1 + sl_pct)
        tp1 = tp2 = tp3 = None
        lev = 1

        if direction != AgentSide.NEUTRAL:
            if direction == AgentSide.LONG:
                sl_dist = price - sl_price
                tp1 = price + sl_dist * 1.5
                tp2 = price + sl_dist * 3.0
                tp3 = price + sl_dist * 5.0
            else:
                sl_dist = sl_price - price
                tp1 = price - sl_dist * 1.5
                tp2 = price - sl_dist * 3.0
                tp3 = price - sl_dist * 5.0

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
