"""
Agente 4: Social Sentiment
Estratégia: Escaneia sentimento de redes sociais para momentum
- Usa notícias e Fear & Greed como proxy de sentimento social
- Só opera com sentimento forte (positivo ou negativo)
- Confiança baseada na magnitude do sentimento
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)


class SocialSentimentAgent(BaseAgent):
    """
    Agente Social Sentiment.
    Opera baseado em sentimento de notícias e Fear & Greed.
    """

    def __init__(self):
        super().__init__(
            name="Social Sentiment",
            description="Escaneia sentimento de notícias e Fear & Greed para momentum.",
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

        # Sentimento social
        sentiment_score = 0.0
        reason_parts = []

        if context:
            fg = getattr(context, "fear_greed", None)
            if fg is not None:
                if fg < 20:
                    sentiment_score += 40
                    reason_parts.append(f"Fear extremo ({fg}) → oportunidade compra")
                elif fg < 35:
                    sentiment_score += 20
                    reason_parts.append(f"Fear moderado ({fg})")
                elif fg > 80:
                    sentiment_score -= 40
                    reason_parts.append(f"Greed extremo ({fg}) → oportunidade venda")
                elif fg > 65:
                    sentiment_score -= 20
                    reason_parts.append(f"Greed moderado ({fg})")

            news = getattr(context, "news_score", None)
            if news is not None:
                sentiment_score += news * 30
                if news > 0.3:
                    reason_parts.append(f"Notícias muito positivas ({news})")
                elif news > 0:
                    reason_parts.append(f"Notícias positivas ({news})")
                elif news < -0.3:
                    reason_parts.append(f"Notícias muito negativas ({news})")
                elif news < 0:
                    reason_parts.append(f"Notícias negativas ({news})")

        # TA confirmation (peso menor)
        rsi = getattr(ind, "rsi", 50) or 50
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)

        ta_confirms = False
        if sentiment_score > 0 and e9 is not None and e21 is not None:
            if e9 > e21:
                ta_confirms = True
                sentiment_score += 10
                reason_parts.append("TA confirma")
        elif sentiment_score < 0 and e9 is not None and e21 is not None:
            if e9 < e21:
                ta_confirms = True
                sentiment_score -= 10
                reason_parts.append("TA confirma")

        direction = AgentSide.NEUTRAL
        confidence = 0.0

        if sentiment_score > 25:
            direction = AgentSide.LONG
            confidence = min(100, 50 + sentiment_score)
        elif sentiment_score < -25:
            direction = AgentSide.SHORT
            confidence = min(100, 50 + abs(sentiment_score))

        # SL/TP
        sl_pct = max(0.005, atr_pct * 1.5)
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
            if confidence >= 80:
                lev = 2

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp_price, 8) if tp_price else None,
            leverage=lev,
            reason=" | ".join(reason_parts) if reason_parts else "neutro",
            regime=str(getattr(getattr(regime, "regime", None), "name", "UNKNOWN")),
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
            metadata={"sentiment_score": sentiment_score},
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={"sentiment": sentiment_score},
        )
