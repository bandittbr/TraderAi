"""
TradeAI - Signal Engine V6 (Phase 8)
Gera sinais com pesos adaptativos calculados pelo Optimizer.

V6 adiciona:
  - parâmetro `weights` (dict[str, float]) com pesos por critério canônico
  - raw_score: contagem simples normalizada (V5)
  - weighted_score: soma ponderada normalizada (V6)
  - confidence = weighted_score quando weights disponível, raw_score caso contrário
  - NÃO altera SL, TP ou gestão de risco
  - Totalmente backward-compatible com V5

Critérios de BUY (6 técnicos + 3 estruturais + 4 SMC = 13 total):
  1. ema_bull          — EMA9  > EMA21
  2. ema_macro_bull    — EMA21 > EMA50
  3. ema_price_above   — EMA50 > EMA200
  4. macd_positive     — MACD  > 0
  5. macd_cross        — Histogram > 0
  6. rsi_ok            — RSI no intervalo [rsi_buy_min, rsi_buy_max]
  7. structure_bullish — Tendência estrutural BULLISH (HH+HL)  [V4]
  8. bos_bullish       — Break of Structure bullish detectado  [V4]
  9. price_near_support— Preço próximo de zona de suporte      [V4]
  10. buy_side_sweep    — Liquidity sweep buy-side recente      [V5]
  11. bullish_fvg       — Fair Value Gap bullish ativo           [V5]
  12. near_hvn_support  — Preço próximo de HVN (suporte vol)    [V5]
  13. liq_score_strong  — Liquidity Score >= 60                 [V5]

Regime-Adaptive (Phase 6 — mantido):
  BULL:           rsi_buy 40–78, buy_min=3, sell_min=4
  BEAR:           rsi_buy 25–50, buy_min=5, sell_min=2
  SIDEWAYS:       rsi_buy 45–65, buy_min=4, sell_min=4
  HIGH_VOLATILITY:rsi_buy 40–68, buy_min=4, sell_min=4
  UNKNOWN:        comportamento padrão
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, Optional
from app.models.indicators import MarketIndicator

# ── Mapeamento critério técnico → critério canônico ───────────────────────────
from app.services.optimizer.criterion_performance import CRITERION_CANONICAL

# ── Tipos ─────────────────────────────────────────────────────────────────────

SignalType = Literal["BUY", "SELL", "NEUTRAL"]

SIGNAL_THRESHOLD = 3

# ── Configuração por regime ───────────────────────────────────────────────────

REGIME_CONFIG: dict[str, dict] = {
    "BULL": {
        "rsi_buy_min": 40.0, "rsi_buy_max": 78.0,
        "rsi_sell_min": 28.0, "rsi_sell_max": 60.0,
        "buy_min_criteria": 3, "sell_min_criteria": 4,
    },
    "BEAR": {
        "rsi_buy_min": 25.0, "rsi_buy_max": 50.0,
        "rsi_sell_min": 40.0, "rsi_sell_max": 70.0,
        "buy_min_criteria": 5, "sell_min_criteria": 2,
    },
    "SIDEWAYS": {
        "rsi_buy_min": 45.0, "rsi_buy_max": 65.0,
        "rsi_sell_min": 35.0, "rsi_sell_max": 55.0,
        "buy_min_criteria": 4, "sell_min_criteria": 4,
    },
    "HIGH_VOLATILITY": {
        "rsi_buy_min": 40.0, "rsi_buy_max": 68.0,
        "rsi_sell_min": 32.0, "rsi_sell_max": 60.0,
        "buy_min_criteria": 4, "sell_min_criteria": 4,
    },
    "UNKNOWN": {
        "rsi_buy_min": 45.0, "rsi_buy_max": 72.0,
        "rsi_sell_min": 28.0, "rsi_sell_max": 55.0,
        "buy_min_criteria": 3, "sell_min_criteria": 3,
    },
}

DEFAULT_WEIGHT = 10.0


@dataclass
class SignalResult:
    signal:          SignalType
    confidence:      int                   # 0–100 (weighted when V6)
    reasons:         list[str] = field(default_factory=list)
    context_boost:   int       = field(default=0)
    criteria_met:    list[str] = field(default_factory=list)
    # V6 additions
    raw_score:       float     = 0.0       # score V5 (0–100, não ponderado)
    weighted_score:  float     = 0.0       # score V6 (0–100, ponderado)
    weights_used:    dict      = field(default_factory=dict)  # {canonical: weight}
    engine_version:  str       = "V5"      # "V5" | "V6"


# ── Engine ────────────────────────────────────────────────────────────────────

def generate_signal(
    indicator:     MarketIndicator,
    current_price: float,
    context=None,   # ContextScore | None (Phase 5)
    regime=None,    # RegimeResult | str | None (Phase 6)
    structure=None, # MarketStructureResult | None (Phase 6.5)
    smc=None,       # SmartMoneyResult | None (Phase 7)
    weights: Optional[dict[str, float]] = None,  # {canonical: float} (Phase 8 V6)
) -> SignalResult:
    """
    Gera sinal de trading com pesos adaptativos (V6) quando disponível.

    Args:
        indicator:     Indicadores técnicos mais recentes.
        current_price: Preço atual do ativo.
        context:       ContextScore opcional (Phase 5+).
        regime:        RegimeResult ou string de regime (Phase 6+).
        structure:     MarketStructureResult opcional (Phase 6.5).
        smc:           SmartMoneyResult opcional (Phase 7).
        weights:       Pesos adaptativos {canonical: float} (Phase 8 V6).
                       Se None, comportamento idêntico ao V5.
    """
    regime_key = _get_regime_key(regime)
    cfg        = REGIME_CONFIG.get(regime_key, REGIME_CONFIG["UNKNOWN"])

    buy_reasons:   list[str] = []
    sell_reasons:  list[str] = []
    buy_criteria:  list[str] = []
    sell_criteria: list[str] = []

    e9   = indicator.ema_9
    e21  = indicator.ema_21
    e50  = indicator.ema_50
    e200 = indicator.ema_200
    macd = indicator.macd
    hist = indicator.macd_histogram
    rsi  = indicator.rsi

    rsi_buy_min  = cfg["rsi_buy_min"]
    rsi_buy_max  = cfg["rsi_buy_max"]
    rsi_sell_min = cfg["rsi_sell_min"]
    rsi_sell_max = cfg["rsi_sell_max"]
    buy_min      = cfg["buy_min_criteria"]
    sell_min     = cfg["sell_min_criteria"]

    # ── Critérios BUY ────────────────────────────────────────────────────────
    if e9 is not None and e21 is not None and e9 > e21:
        buy_reasons.append("EMA9 > EMA21")
        buy_criteria.append("ema_bull")
    if e21 is not None and e50 is not None and e21 > e50:
        buy_reasons.append("EMA21 > EMA50")
        buy_criteria.append("ema_macro_bull")
    if e50 is not None and e200 is not None and e50 > e200:
        buy_reasons.append("EMA50 > EMA200")
        buy_criteria.append("ema_price_above")
    if macd is not None and macd > 0:
        buy_reasons.append("MACD positivo")
        buy_criteria.append("macd_positive")
    if hist is not None and hist > 0:
        buy_reasons.append("Histogram positivo")
        buy_criteria.append("macd_cross")
    if rsi is not None and rsi_buy_min <= rsi <= rsi_buy_max:
        buy_reasons.append(f"RSI em zona de compra [{rsi_buy_min:.0f}–{rsi_buy_max:.0f}] ({rsi:.1f})")
        buy_criteria.append("rsi_ok")

    # ── Critérios SELL ───────────────────────────────────────────────────────
    if e9 is not None and e21 is not None and e9 < e21:
        sell_reasons.append("EMA9 < EMA21")
        sell_criteria.append("ema_bear")
    if e21 is not None and e50 is not None and e21 < e50:
        sell_reasons.append("EMA21 < EMA50")
        sell_criteria.append("ema_macro_bear")
    if e50 is not None and e200 is not None and e50 < e200:
        sell_reasons.append("EMA50 < EMA200")
        sell_criteria.append("ema_price_below")
    if macd is not None and macd < 0:
        sell_reasons.append("MACD negativo")
        sell_criteria.append("macd_negative")
    if hist is not None and hist < 0:
        sell_reasons.append("Histogram negativo")
        sell_criteria.append("macd_cross_bear")
    if rsi is not None and rsi_sell_min <= rsi <= rsi_sell_max:
        sell_reasons.append(f"RSI em zona de venda [{rsi_sell_min:.0f}–{rsi_sell_max:.0f}] ({rsi:.1f})")
        sell_criteria.append("rsi_sell")

    # ── Critérios Market Structure V4 ────────────────────────────────────────
    if structure is not None:
        struct_trend = getattr(structure, "trend", None)
        trend_val    = struct_trend.value if hasattr(struct_trend, "value") else str(struct_trend)

        if trend_val == "BULLISH":
            buy_reasons.append(f"Estrutura BULLISH ({structure.structure_label})")
            buy_criteria.append("structure_bullish")
        elif trend_val == "BEARISH":
            sell_reasons.append(f"Estrutura BEARISH ({structure.structure_label})")
            sell_criteria.append("structure_bearish")

        if getattr(structure, "bos_bullish", False):
            buy_reasons.append("BOS Bullish detectado")
            buy_criteria.append("bos_bullish")
        if getattr(structure, "bos_bearish", False):
            sell_reasons.append("BOS Bearish detectado")
            sell_criteria.append("bos_bearish")
        if getattr(structure, "price_near_support", False):
            buy_reasons.append("Preço próximo de suporte")
            buy_criteria.append("price_near_support")
        if getattr(structure, "price_near_resistance", False):
            sell_reasons.append("Preço próximo de resistência")
            sell_criteria.append("price_near_resistance")

    has_structure = structure is not None

    # ── Critérios Smart Money V5 ──────────────────────────────────────────────
    has_smc = smc is not None
    if has_smc:
        if getattr(smc, "has_recent_buy_sweep", False):
            buy_reasons.append("Buy-side liquidity sweep recente")
            buy_criteria.append("buy_side_sweep")
        if getattr(smc, "has_bullish_fvg", False):
            dist = getattr(smc, "bullish_fvg_distance_pct", 99.0)
            buy_reasons.append(f"Bullish FVG ativo ({dist:.2f}%)")
            buy_criteria.append("bullish_fvg")
        if getattr(smc, "near_hvn", False) and not getattr(smc, "price_above_poc", True):
            buy_reasons.append("Preço em HVN (suporte de volume)")
            buy_criteria.append("near_hvn_support")
        if getattr(smc, "liq_score_strong", False) and getattr(smc, "sweep_bias", "") == "BULLISH":
            buy_reasons.append(f"Liquidity Score forte ({smc.liquidity_score:.0f}/100)")
            buy_criteria.append("liq_score_strong_buy")

        if getattr(smc, "has_recent_sell_sweep", False):
            sell_reasons.append("Sell-side liquidity sweep recente")
            sell_criteria.append("sell_side_sweep")
        if getattr(smc, "has_bearish_fvg", False):
            dist = getattr(smc, "bearish_fvg_distance_pct", 99.0)
            sell_reasons.append(f"Bearish FVG ativo ({dist:.2f}%)")
            sell_criteria.append("bearish_fvg")
        if getattr(smc, "near_hvn", False) and getattr(smc, "price_above_poc", False):
            sell_reasons.append("Preço em HVN (resistência de volume)")
            sell_criteria.append("near_hvn_resistance")
        if getattr(smc, "liq_score_strong", False) and getattr(smc, "sweep_bias", "") == "BEARISH":
            sell_reasons.append(f"Liquidity Score forte ({smc.liquidity_score:.0f}/100)")
            sell_criteria.append("liq_score_strong_sell")

    buy_count  = len(buy_reasons)
    sell_count = len(sell_reasons)
    total_max  = 13 if (has_structure and has_smc) else (9 if has_structure else (13 if has_smc else 6))

    if regime_key not in ("UNKNOWN",):
        regime_note = f"[Regime: {regime_key}] min_buy={buy_min}, min_sell={sell_min}"
    else:
        regime_note = None

    # ── V6: Calcular scores ───────────────────────────────────────────────────
    is_v6          = weights is not None and len(weights) > 0
    engine_version = "V6" if is_v6 else "V5"

    def _raw_score(count: int) -> float:
        return round((count / total_max) * 100.0, 2) if total_max > 0 else 0.0

    def _weighted_score(criteria_list: list[str], all_weights: dict[str, float]) -> tuple[float, dict]:
        """Soma pesos dos critérios atendidos / soma total de pesos possíveis."""
        if not criteria_list:
            return 0.0, {}
        used = {}
        total_w = 0.0
        met_w   = 0.0
        # Soma peso de cada critério canônico possível
        all_canonicals_seen: set[str] = set()
        for c in criteria_list:
            can = CRITERION_CANONICAL.get(c, c)
            if can not in all_canonicals_seen:
                all_canonicals_seen.add(can)
                w = all_weights.get(can, DEFAULT_WEIGHT)
                met_w += w
                used[can] = w
        # Total possível: soma todos os pesos distintos do lado
        total_w = total_max * DEFAULT_WEIGHT  # escala relativa
        score = min(100.0, round((met_w / max(total_w, 1.0)) * 100.0, 2))
        return score, used

    # ── Determinação do sinal ─────────────────────────────────────────────────
    if buy_count >= buy_min and buy_count > sell_count:
        raw_s = _raw_score(buy_count)
        if is_v6:
            w_s, used_w = _weighted_score(buy_criteria, weights)
            confidence  = int(round(w_s))
        else:
            w_s, used_w = raw_s, {}
            confidence  = int(round(raw_s))

        reasons = list(buy_reasons)
        if regime_note:
            reasons.append(regime_note)
        if is_v6:
            reasons.append(f"[V6] weighted_score={w_s:.1f} raw={raw_s:.1f}")

        return _apply_context_boost(SignalResult(
            signal         = "BUY",
            confidence     = min(confidence, 100),
            reasons        = reasons,
            criteria_met   = buy_criteria,
            raw_score      = raw_s,
            weighted_score = w_s,
            weights_used   = used_w,
            engine_version = engine_version,
        ), context)

    if sell_count >= sell_min and sell_count > buy_count:
        raw_s = _raw_score(sell_count)
        if is_v6:
            w_s, used_w = _weighted_score(sell_criteria, weights)
            confidence  = int(round(w_s))
        else:
            w_s, used_w = raw_s, {}
            confidence  = int(round(raw_s))

        reasons = list(sell_reasons)
        if regime_note:
            reasons.append(regime_note)
        if is_v6:
            reasons.append(f"[V6] weighted_score={w_s:.1f} raw={raw_s:.1f}")

        return _apply_context_boost(SignalResult(
            signal         = "SELL",
            confidence     = min(confidence, 100),
            reasons        = reasons,
            criteria_met   = sell_criteria,
            raw_score      = raw_s,
            weighted_score = w_s,
            weights_used   = used_w,
            engine_version = engine_version,
        ), context)

    # Neutral
    neutral_reasons = []
    if buy_count > 0:
        neutral_reasons.extend([f"↑ {r}" for r in buy_reasons[:2]])
    if sell_count > 0:
        neutral_reasons.extend([f"↓ {r}" for r in sell_reasons[:2]])
    if regime_note:
        neutral_reasons.append(regime_note)

    max_signals = max(buy_count, sell_count)
    raw_s = _raw_score(max_signals)
    confidence = int(round(raw_s))

    return _apply_context_boost(SignalResult(
        signal         = "NEUTRAL",
        confidence     = confidence,
        reasons        = neutral_reasons,
        criteria_met   = buy_criteria + sell_criteria,
        raw_score      = raw_s,
        weighted_score = raw_s,
        engine_version = engine_version,
    ), context)


def _get_regime_key(regime) -> str:
    if regime is None:
        return "UNKNOWN"
    if hasattr(regime, "regime"):
        val = regime.regime
        return val.value if hasattr(val, "value") else str(val)
    if hasattr(regime, "value"):
        return regime.value
    return str(regime)


# ── Context Boost (Phase 5 — sem alteração) ──────────────────────────────────

def _apply_context_boost(result: SignalResult, context) -> SignalResult:
    if context is None:
        return result
    boost = 0
    if context.news_score >= 65 and result.signal == "BUY":
        boost += 10
        result.reasons.append("Notícias positivas confirmam BUY")
    elif context.news_score <= 35 and result.signal == "BUY":
        boost -= 10
        result.reasons.append("Notícias negativas enfraquecem BUY")
    elif context.news_score >= 65 and result.signal == "SELL":
        boost -= 10
    elif context.news_score <= 35 and result.signal == "SELL":
        boost += 10
        result.reasons.append("Notícias negativas confirmam SELL")
    if context.fear_greed <= 25 and result.signal == "BUY":
        boost -= 5
    elif context.fear_greed >= 75 and result.signal == "SELL":
        boost -= 5
    if context.funding_label == "BULLISH" and result.signal == "BUY":
        boost += 5
    elif context.funding_label == "BEARISH" and result.signal == "SELL":
        boost += 5
    elif context.funding_label == "BULLISH" and result.signal == "SELL":
        boost -= 5
    elif context.funding_label == "BEARISH" and result.signal == "BUY":
        boost -= 5
    new_confidence      = max(0, min(100, result.confidence + boost))
    result.confidence   = new_confidence
    result.context_boost = boost
    return result
