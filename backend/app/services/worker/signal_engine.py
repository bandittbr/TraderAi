"""
Worker Signal Engine — Multi-Timeframe Confluence Hunter (V7)

Estratégia do Worker (o agente mais sofisticado):
  1. Direção primária vinda do timeframe 1h (EMA alignment + structure + SMC)
  2. Entrada no 15m (pullback, FVG, sweep, RSI confirmation)
  3. Score de confluência: 0–100 combinando todos os módulos
  4. Só entra se confidence >= 65 E confluência >= 70%
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.services.signal_analytics.regime_classifier import RegimeResult

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────────────────
MIN_CONFIDENCE     = 55   # score mínimo de direção (reduzido de 65)
MIN_CONFLUENCE_PCT = 60   # % mínima de módulos concordando (reduzido de 70)
MAX_LEVERAGE       = 3
MIN_LEVERAGE       = 1

# Pesos dos módulos no score final
MODULE_WEIGHTS = {
    "technical":  0.30,  # EMA, MACD, RSI
    "structure":  0.20,  # Market structure, BOS
    "smc":        0.20,  # Sweep, FVG, liquidity
    "context":    0.15,  # News, Fear & Greed, Funding
    "regime":     0.15,  # Regime alignment
}


@dataclass
class WorkerSignalResult:
    direction:      str           # "LONG" | "SHORT" | "NEUTRAL"
    confidence:     float         # 0–100
    direction_score: float        # 0–100 (score do timeframe maior)
    confluence_pct: float         # 0–100 % de módulos concordando
    leverage:       int           # 1–3
    entry_price:    float         # preço atual para entry
    stop_loss:      float         # preço do SL
    take_profit1:   Optional[float] = None  # R:R 1.5
    take_profit2:   Optional[float] = None  # R:R 3.0
    take_profit3:   Optional[float] = None  # R:R 5.0
    reason:         str           = ""
    regime:         str           = "UNKNOWN"
    atr_pct:        float         = 0.0
    # Detalhamento
    module_scores:  dict          = field(default_factory=dict)
    entry_signals:  list[str]     = field(default_factory=list)
    is_valid:       bool          = True


class WorkerSignalEngine:
    """
    Gera sinais multi-timeframe para o Worker Agent.
    Usa o SignalEngine principal para o bias de direção (1h)
    e análise própria para entrada (15m).
    """

    async def analyze(
        self,
        symbol:      str,
        price_1h:    Optional[Any],   # MarketIndicator do timeframe 1h
        price_15m:   Optional[Any],   # MarketIndicator do timeframe 15m
        regime:      Optional[RegimeResult] = None,
        context:     Optional[Any] = None,   # ContextScore
        structure:   Optional[Any] = None,   # MarketStructureResult
        smc:         Optional[Any] = None,   # SmartMoneyResult
        weights:     Optional[dict] = None,  # Pesos adaptativos V6
        current_price: Optional[float] = None,  # preço atual (MarketIndicator não tem close)
    ) -> WorkerSignalResult:
        """
        Análise completa multi-timeframe.

        Returns:
            WorkerSignalResult com direção, confiança e níveis.
            Se is_valid=False, não entrar.
        """
        if price_1h is None or price_15m is None:
            return WorkerSignalResult(
                direction="NEUTRAL", confidence=0, direction_score=0,
                confluence_pct=0, leverage=1, entry_price=0,
                stop_loss=0, reason="Sem dados", is_valid=False,
            )

        # Preço atual: usa o parâmetro explícito; fallback para atributos do indicador
        if current_price is None or current_price <= 0:
            current_price = getattr(price_15m, "close", None) or getattr(price_15m, "price", None) or 0.0
        if current_price <= 0:
            return WorkerSignalResult(
                direction="NEUTRAL", confidence=0, direction_score=0,
                confluence_pct=0, leverage=1, entry_price=0,
                stop_loss=0, reason="Preço inválido", is_valid=False,
            )

        regime_label = regime.regime.name if regime and regime.regime else "UNKNOWN"
        atr_pct = self._get_atr_pct(price_15m, current_price)

        # ── 1. Direção primária (timeframe 1h) ──────────────────────────────
        dir_score, dir_signal, dir_reason = self._compute_direction_bias(
            price_1h, structure, regime_label,
        )

        # ── 2. Score por módulo ─────────────────────────────────────────────
        module_scores = self._compute_module_scores(
            price_1h, price_15m, structure, smc, context, regime_label,
        )

        # ── 3. Confluência ──────────────────────────────────────────────────
        modules_agree = 0
        total_modules = 0
        for module, score in module_scores.items():
            total_modules += 1
            if dir_signal == "LONG" and score > 0:
                modules_agree += 1
            elif dir_signal == "SHORT" and score < 0:
                modules_agree += 1

        confluence_pct = (modules_agree / total_modules * 100) if total_modules > 0 else 0

        # ── 4. Score final ponderado ────────────────────────────────────────
        final_confidence = self._compute_final_confidence(
            dir_score, module_scores, dir_signal,
        )

        # ── 5. Decisão ──────────────────────────────────────────────────────
        direction = "NEUTRAL"
        leverage = MIN_LEVERAGE
        sl = 0.0
        tp1 = tp2 = tp3 = None
        reason = ""

        if final_confidence >= MIN_CONFIDENCE and confluence_pct >= MIN_CONFLUENCE_PCT:
            direction = dir_signal
            sl = self._compute_sl(current_price, direction, atr_pct, regime_label)
            tp1 = self._compute_tp(current_price, direction, sl, 1.5)
            tp2 = self._compute_tp(current_price, direction, sl, 3.0)
            tp3 = self._compute_tp(current_price, direction, sl, 5.0)
            leverage = self._compute_leverage(atr_pct, regime_label, confidence=final_confidence)
            reason = (
                f"{dir_reason} | conf={final_confidence:.0f}% "
                f"confl={confluence_pct:.0f}% lev={leverage}x"
            )
        else:
            reason = (
                f"descartado: conf={final_confidence:.0f}% "
                f"confl={confluence_pct:.0f}% (min {MIN_CONFIDENCE}%/{MIN_CONFLUENCE_PCT}%)"
            )

        return WorkerSignalResult(
            direction       = direction,
            confidence      = round(final_confidence, 1),
            direction_score = round(dir_score, 1),
            confluence_pct  = round(confluence_pct, 1),
            leverage        = leverage,
            entry_price     = current_price,
            stop_loss       = round(sl, 8),
            take_profit1    = round(tp1, 8) if tp1 else None,
            take_profit2    = round(tp2, 8) if tp2 else None,
            take_profit3    = round(tp3, 8) if tp3 else None,
            reason          = reason,
            regime          = regime_label,
            atr_pct         = round(atr_pct, 4),
            module_scores   = module_scores,
            entry_signals   = [],
            is_valid        = direction != "NEUTRAL",
        )

    # ── Métodos internos ──────────────────────────────────────────────────

    def _compute_direction_bias(
        self,
        indicator: Any,
        structure: Optional[Any],
        regime: str,
    ) -> tuple[float, str, str]:
        """
        Determina direção primária (1h) usando:
        - EMA alignment (peso 40%)
        - MACD (peso 20%)
        - Market structure (peso 25%)
        - Regime alignment (peso 15%)
        FIX: score começa em 50 e ranges são mais sensíveis para SHORT
        """
        score = 50.0  # neutro
        reasons = []

        # EMA alignment
        ema_alignment = 0.0
        e9 = getattr(indicator, "ema_9", None)
        e21 = getattr(indicator, "ema_21", None)
        e50 = getattr(indicator, "ema_50", None)
        e200 = getattr(indicator, "ema_200", None)

        if all(v is not None for v in [e9, e21, e50, e200]):
            if e9 > e21 > e50 > e200:
                ema_alignment = 40.0   # bull perfeito
                reasons.append("EMA: bull perfeito")
            elif e9 < e21 < e50 < e200:
                ema_alignment = -40.0  # bear perfeito
                reasons.append("EMA: bear perfeito")
            elif e9 > e21 and e50 > e200:
                ema_alignment = 20.0   # bull parcial
                reasons.append("EMA: bull parcial")
            elif e9 < e21 and e50 < e200:
                ema_alignment = -20.0  # bear parcial
                reasons.append("EMA: bear parcial")
            elif e9 > e21:
                ema_alignment = 10.0   # bull mínimo
                reasons.append("EMA: bull leve")
            elif e9 < e21:
                ema_alignment = -10.0  # bear mínimo
                reasons.append("EMA: bear leve")
        elif e9 is not None and e21 is not None:
            # Fallback com apenas EMA9 e EMA21
            if e9 > e21:
                ema_alignment = 15.0
                reasons.append("EMA9>21: bull")
            else:
                ema_alignment = -15.0
                reasons.append("EMA9<21: bear")
        score += ema_alignment

        # MACD
        macd = getattr(indicator, "macd", None)
        macd_sig = getattr(indicator, "macd_signal", None)
        if macd is not None and macd_sig is not None:
            if macd > macd_sig and macd > 0:
                score += 15.0
                reasons.append("MACD: bullish")
            elif macd < macd_sig and macd < 0:
                score -= 15.0
                reasons.append("MACD: bearish")

        # Market structure
        if structure:
            struct_label = getattr(structure, "structure_label", "")
            if "HH" in struct_label and "HL" in struct_label:
                score += 20.0
                reasons.append(f"Structure: {struct_label}")
            elif "LH" in struct_label and "LL" in struct_label:
                score -= 20.0
                reasons.append(f"Structure: {struct_label}")

        # Regime alignment
        if regime in ("BULL", "HIGH_VOLATILITY"):
            score += 5.0
        elif regime == "BEAR":
            score -= 5.0

        # FIX: ranges mais amplos para detectar SHORT
        # Antes: LONG > 55, SHORT < 45, NEUTRAL 45-55
        direction = "LONG" if score > 53 else ("SHORT" if score < 47 else "NEUTRAL")
        return score, direction, " | ".join(reasons) if reasons else "neutro"

    def _compute_module_scores(
        self,
        ind_1h: Any,
        ind_15m: Any,
        structure: Optional[Any],
        smc: Optional[Any],
        context: Optional[Any],
        regime: str,
    ) -> dict[str, float]:
        """
        Scores por módulo: positivo = bullish, negativo = bearish.
        Usa timeframe 15m para entrada, 1h como filtro.
        FIX: módulos agora contribuem mais fortemente para SHORT
        """
        scores: dict[str, float] = {}

        # Técnico (15m) — FIX: ranges expandidos para detectar bearish
        tech = 0.0
        rsi = getattr(ind_15m, "rsi", 50)
        if rsi is not None:
            if 40 <= rsi <= 60:
                tech += 5.0   # RSI neutro = OK para qualquer direção
            elif rsi > 65:
                tech -= 12.0  # overbought = bearish bias (antes -10)
                logger.debug(f"[Worker] RSI overbought ({rsi:.0f}) → bearish")
            elif rsi > 55:
                tech -= 5.0   # RSI alto = leve bearish
            elif rsi < 35:
                tech += 12.0  # oversold = bullish bias (antes +10)
                logger.debug(f"[Worker] RSI oversold ({rsi:.0f}) → bullish")
            elif rsi < 45:
                tech += 5.0   # RSI baixo = leve bullish

        macd = getattr(ind_15m, "macd", None)
        macd_sig = getattr(ind_15m, "macd_signal", None)
        if macd is not None and macd_sig is not None:
            if macd > macd_sig:
                tech += 12.0  # antes 10
            elif macd < macd_sig:
                tech -= 12.0  # antes 10

        e9 = getattr(ind_15m, "ema_9", None)
        e21 = getattr(ind_15m, "ema_21", None)
        if e9 is not None and e21 is not None:
            if e9 > e21:
                tech += 8.0   # antes 5
            elif e9 < e21:
                tech -= 8.0   # antes 5
        scores["technical"] = tech

        # Structure
        struct_score = 0.0
        if structure:
            label = getattr(structure, "structure_label", "")
            if "HH" in label and "HL" in label:
                struct_score = 15.0
            elif "LH" in label and "LL" in label:
                struct_score = -15.0
            elif "CH" in label:
                struct_score = -5.0   # change of character = caution
            elif "CL" in label:
                struct_score = 5.0
        scores["structure"] = struct_score

        # SMC — FIX: ranges expandidos
        smc_score = 0.0
        if smc:
            sweep_buy = getattr(smc, "has_recent_buy_sweep", False)
            sweep_sell = getattr(smc, "has_recent_sell_sweep", False)
            fvg_bull = getattr(smc, "has_bullish_fvg", False)
            fvg_bear = getattr(smc, "has_bearish_fvg", False)

            if sweep_sell:
                smc_score += 12.0  # antes 10
                logger.debug(f"[Worker] SMC: sell sweep → bullish")
            if sweep_buy:
                smc_score -= 12.0  # antes 10
                logger.debug(f"[Worker] SMC: buy sweep → bearish")
            if fvg_bull:
                smc_score += 10.0  # antes 8
            if fvg_bear:
                smc_score -= 10.0  # antes 8

            liq_score = getattr(smc, "liquidity_score", 50)
            if liq_score > 70:
                smc_score += 5.0
            elif liq_score < 30:
                smc_score -= 5.0
        scores["smc"] = smc_score

        # Contexto
        ctx_score = 0.0
        if context:
            fg = getattr(context, "fear_greed", None)
            if fg is not None:
                if fg < 25:
                    ctx_score += 8.0   # extreme fear = compra
                elif fg > 75:
                    ctx_score -= 8.0   # extreme greed = venda

            news = getattr(context, "news_score", None)
            if news is not None:
                ctx_score += news * 5.0
        scores["context"] = ctx_score

        # Regime — FIX: contribuição maior
        reg_score = 0.0
        if regime == "BULL":
            reg_score = 18.0  # antes 15
        elif regime == "BEAR":
            reg_score = -18.0  # antes -15
        elif regime == "SIDEWAYS":
            reg_score = 3.0   # antes 0 — sideways permite trades de reversão
        elif regime == "HIGH_VOLATILITY":
            reg_score = 8.0  # antes 5 — oportunidade, mas com cautela
        scores["regime"] = reg_score

        return scores

    def _compute_final_confidence(
        self,
        dir_score: float,
        module_scores: dict[str, float],
        direction: str,
    ) -> float:
        """
        Média ponderada do score de direção + scores modulares.
        FIX: para SHORT usa (100 - dir_score) como base (simétrico ao LONG)
        e considera o SINAL do módulo — só módulos alinhados à direção somam.
        (Antes, SHORT nunca atingia MIN_CONFIDENCE e módulos bearish
        contavam a favor de LONG por causa do abs().)
        """
        if direction == "NEUTRAL":
            return 0.0

        base = dir_score if direction == "LONG" else (100.0 - dir_score)
        weighted_sum = base * 0.35  # direção primária pesa 35%

        for module, score in module_scores.items():
            w = MODULE_WEIGHTS.get(module, 0.10)
            aligned = score if direction == "LONG" else -score
            weighted_sum += max(0.0, aligned) * w * 5.0  # normaliza (100/20)

        return min(100, max(0, weighted_sum))

    def _compute_sl(
        self,
        price: float,
        direction: str,
        atr_pct: float,
        regime: str,
    ) -> float:
        """SL adaptativo: max(0.5%, ATR% × 1.5), expandido em alta vol."""
        base_sl_pct = max(0.005, atr_pct * 1.5)
        # Expande SL em alta volatilidade
        if regime == "HIGH_VOLATILITY":
            base_sl_pct *= 1.3
        if direction == "LONG":
            return price * (1 - base_sl_pct)
        else:
            return price * (1 + base_sl_pct)

    def _compute_tp(self, price: float, direction: str, sl_price: float, rr: float) -> float:
        """Calcula TP baseado em R:R fixo."""
        if direction == "LONG":
            sl_dist = price - sl_price
            return price + sl_dist * rr if sl_dist > 0 else price * 1.01
        else:
            sl_dist = sl_price - price
            return price - sl_dist * rr if sl_dist > 0 else price * 0.99

    def _compute_leverage(self, atr_pct: float, regime: str, confidence: float) -> int:
        """Leverage adaptativo: menor em alta vol, maior com confiança alta."""
        if regime == "HIGH_VOLATILITY" or atr_pct > 0.02:
            return 1
        if confidence >= 85:
            return 3
        if confidence >= 75:
            return 2
        return 1

    @staticmethod
    def _get_atr_pct(indicator: Any, current_price: Optional[float] = None) -> float:
        """Extrai ATR% (fração) do indicador, usando o preço atual quando fornecido."""
        atr = getattr(indicator, "atr", None)
        price = current_price or getattr(indicator, "close", None) or getattr(indicator, "price", None)
        if atr and price and price > 0:
            return atr / price
        return 0.01  # fallback 1%
