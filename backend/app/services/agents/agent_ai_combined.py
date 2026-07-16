"""
Agente 3: AI Combined Analysis
Estratégia: Pondera TA + News + Macro + Community
- Usa análise técnica como base
- Ajusta score com notícias, Fear & Greed, funding
- Combina múltiplas fontes em score final
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.services.agents.base import BaseAgent, AgentSignal, AgentSide, AgentResult

logger = logging.getLogger(__name__)

# Pesos
W_TA = 0.40
W_NEWS = 0.20
W_MACRO = 0.20
W_COMMUNITY = 0.20


class AICombinedAnalysisAgent(BaseAgent):
    """
    Agente AI Combined Analysis.
    Pondera TA + News + Macro + Community em score final.
    """

    def __init__(self):
        super().__init__(
            name="AI Combined",
            description="Combina TA + News + Macro + Community em score final ponderado.",
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

        # ── TA Score (40%) ──
        rsi = getattr(ind, "rsi", 50) or 50
        e9 = getattr(ind, "ema_9", None)
        e21 = getattr(ind, "ema_21", None)
        macd = getattr(ind, "macd", None)
        macd_sig = getattr(ind, "macd_signal", None)
        atr = getattr(ind, "atr", None)
        atr_pct = (atr / price) if atr and price > 0 else 0.01

        ta_score = 0.0
        ta_reasons = []

        # EMA
        if e9 is not None and e21 is not None:
            if e9 > e21:
                ta_score += 20
                ta_reasons.append("EMA altista")
            else:
                ta_score -= 20
                ta_reasons.append("EMA baixista")

        # RSI
        if rsi < 30:
            ta_score += 15
            ta_reasons.append(f"RSI oversold ({rsi:.0f})")
        elif rsi > 70:
            ta_score -= 15
            ta_reasons.append(f"RSI overbought ({rsi:.0f})")
        elif 40 <= rsi <= 60:
            ta_score += 5
            ta_reasons.append(f"RSI neutro ({rsi:.0f})")

        # MACD
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                ta_score += 15
                ta_reasons.append("MACD altista")
            elif macd < macd_sig:
                ta_score -= 15
                ta_reasons.append("MACD baixista")

        ta_normalized = max(-100, min(100, ta_score))

        # ── News Score (20%) ──
        news_score = 0.0
        news_reasons = []
        if context:
            fg = getattr(context, "fear_greed", None)
            if fg is not None:
                if fg < 25:
                    news_score += 30
                    news_reasons.append(f"Fear extremo ({fg})")
                elif fg > 75:
                    news_score -= 30
                    news_reasons.append(f"Greed extremo ({fg})")

            ctx_news = getattr(context, "news_score", None)
            if ctx_news is not None:
                news_score += ctx_news * 20
                if ctx_news > 0:
                    news_reasons.append(f"Notícias positivas ({ctx_news})")
                elif ctx_news < 0:
                    news_reasons.append(f"Notícias negativas ({ctx_news})")

        news_normalized = max(-100, min(100, news_score))

        # ── Macro/Regime Score (20%) ──
        macro_score = 0.0
        macro_reasons = []
        regime_label = getattr(regime, "regime", None)
        if regime_label:
            regime_str = regime_label.name if hasattr(regime_label, "name") else str(regime_label)
            if regime_str == "BULL":
                macro_score += 40
                macro_reasons.append("Regime BULL")
            elif regime_str == "BEAR":
                macro_score -= 40
                macro_reasons.append("Regime BEAR")
            elif regime_str == "HIGH_VOLATILITY":
                macro_score += 10
                macro_reasons.append("Alta volatilidade")

        # ── Community/Structure Score (20%) ──
        community_score = 0.0
        community_reasons = []
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "HH" in struct_label and "HL" in struct_label:
                community_score += 30
                community_reasons.append(f"Estrutura altista ({struct_label})")
            elif "LH" in struct_label and "LL" in struct_label:
                community_score -= 30
                community_reasons.append(f"Estrutura baixista ({struct_label})")

        if smc:
            liq = getattr(smc, "liquidity_score", 50)
            if liq > 70:
                community_score += 10
                community_reasons.append("Liquidez alta")
            elif liq < 30:
                community_score -= 10
                community_reasons.append("Liquidez baixa")

        # ── Score Final Ponderado ──
        final_score = (
            ta_normalized * W_TA +
            news_normalized * W_NEWS +
            macro_score * W_MACRO +
            community_score * W_COMMUNITY
        )

        direction = AgentSide.NEUTRAL
        confidence = 0.0
        if final_score > 15:
            direction = AgentSide.LONG
            confidence = min(100, 50 + final_score * 0.5)
        elif final_score < -15:
            direction = AgentSide.SHORT
            confidence = min(100, 50 + abs(final_score) * 0.5)

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

        all_reasons = ta_reasons + news_reasons + macro_reasons + community_reasons
        reason = " | ".join(all_reasons) if all_reasons else "neutro"

        signal = AgentSignal(
            agent_name=self.name, symbol=symbol,
            direction=direction, confidence=confidence,
            entry_price=price, stop_loss=round(sl_price, 8),
            take_profit=round(tp_price, 8) if tp_price else None,
            leverage=lev, reason=reason,
            regime=str(regime_label) if regime_label else "UNKNOWN",
            atr_pct=atr_pct, is_valid=direction != AgentSide.NEUTRAL,
            metadata={
                "ta_score": ta_normalized,
                "news_score": news_normalized,
                "macro_score": macro_score,
                "community_score": community_score,
                "final_score": final_score,
            },
        )

        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return AgentResult(
            agent_name=self.name, symbol=symbol,
            signal=signal, execution_time_ms=elapsed,
            module_scores={
                "ta": ta_normalized, "news": news_normalized,
                "macro": macro_score, "community": community_score,
                "final": final_score,
            },
        )
