"""
Fase 11 — Strategy Generator
Gera sistematicamente combinações de critérios em JSON auditável.
Cada estratégia = entry_rules + exit_rules + risk_rules.
Determinístico: nenhum random — usa produto cartesiano controlado.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Parâmetros geradores ───────────────────────────────────────────────────────

# Entry criteria disponíveis (boolean on/off)
ENTRY_CRITERIA = [
    "rsi_oversold",       # RSI < threshold
    "rsi_overbought",     # RSI > threshold (para SHORT)
    "macd_bullish",       # MACD cross bullish
    "macd_bearish",       # MACD cross bearish
    "ema_trend_up",       # preço acima da EMA lenta
    "ema_trend_down",     # preço abaixo da EMA lenta
    "bos_detected",       # Break of Structure confirmado
    "choch_detected",     # Change of Character
    "fvg_present",        # Fair Value Gap na zona
    "sweep_present",      # Liquidity Sweep recente
    "hvn_support",        # HVN como suporte (Volume Profile)
    "fear_extreme",       # Fear & Greed < 25
    "greed_extreme",      # Fear & Greed > 75
    "funding_negative",   # Funding Rate negativo
    "oi_increasing",      # Open Interest crescendo
    "context_bullish",    # Context Score >= 65
]

# Parâmetros quantitativos das entry rules
RSI_THRESHOLDS    = [25, 30, 35]
EMA_COMBOS        = [("20","50"), ("50","200"), ("20","200")]
CONTEXT_MINS      = [50, 60, 70]

# Exit rules
TP_ATR_MULTS      = [1.5, 2.0, 3.0]
SL_ATR_MULTS      = [0.5, 1.0, 1.5]
MAX_HOLD_CANDLES  = [12, 24, 48]

# Risk rules
MIN_CONFLUENCE    = [2, 3, 4]
REGIME_FILTERS    = [
    ["BULL"],
    ["BULL", "SIDEWAYS"],
    ["BULL", "BEAR", "SIDEWAYS", "HIGH_VOLATILITY"],  # todos
]

# Limite de estratégias geradas (evita explosão combinatória)
MAX_STRATEGIES    = 5000
MIN_ENTRY_CRITERIA = 2
MAX_ENTRY_CRITERIA = 4


# ── Dataclass ─────────────────────────────────────────────────────────────────

@dataclass
class StrategyDef:
    """Definição completa de uma estratégia em JSON-auditável."""
    strategy_key: str
    name:         str
    entry_rules:  dict
    exit_rules:   dict
    risk_rules:   dict
    generation:   int = 0
    origin:       str = "GENERATED"
    parent_ids:   list = field(default_factory=list)


# ── Generator ─────────────────────────────────────────────────────────────────

class StrategyGenerator:
    """
    Gera sistematicamente estratégias via produto cartesiano controlado.
    Sem IA, sem random — apenas combinatorics determinístico.
    """

    def generate_all(self, limit: int = MAX_STRATEGIES) -> list[StrategyDef]:
        """Gera todas as combinações até o limite."""
        strategies: list[StrategyDef] = []
        seen_keys: set[str] = set()

        for n_criteria in range(MIN_ENTRY_CRITERIA, MAX_ENTRY_CRITERIA + 1):
            for criteria_combo in itertools.combinations(ENTRY_CRITERIA, n_criteria):
                # Filtrar combinações incoerentes
                if not _is_coherent(list(criteria_combo)):
                    continue

                for tp_mult in TP_ATR_MULTS:
                    for sl_mult in SL_ATR_MULTS:
                        if tp_mult <= sl_mult:
                            continue   # RR < 1 — inválido
                        for hold in MAX_HOLD_CANDLES:
                            for conf in MIN_CONFLUENCE:
                                if conf > n_criteria:
                                    continue  # impossível atingir
                                for regimes in REGIME_FILTERS:
                                    entry  = _build_entry(list(criteria_combo))
                                    exit_r = _build_exit(tp_mult, sl_mult, hold)
                                    risk   = _build_risk(conf, regimes)

                                    key  = _make_key(entry, exit_r, risk)
                                    if key in seen_keys:
                                        continue
                                    seen_keys.add(key)

                                    name = _make_name(list(criteria_combo), tp_mult, sl_mult, regimes)
                                    strategies.append(StrategyDef(
                                        strategy_key = key,
                                        name         = name,
                                        entry_rules  = entry,
                                        exit_rules   = exit_r,
                                        risk_rules   = risk,
                                    ))
                                    if len(strategies) >= limit:
                                        logger.info("[generator] limite %d atingido", limit)
                                        return strategies

        logger.info("[generator] %d estratégias geradas", len(strategies))
        return strategies

    def mutate(self, base: StrategyDef, seed: int = 0) -> list[StrategyDef]:
        """Gera mutações de uma estratégia base (alterando um parâmetro por vez)."""
        mutations: list[StrategyDef] = []

        # Mutar TP multiplier
        for tp in TP_ATR_MULTS:
            if tp == base.exit_rules.get("take_profit_atr_mult"):
                continue
            new_exit = dict(base.exit_rules)
            new_exit["take_profit_atr_mult"] = tp
            key  = _make_key(base.entry_rules, new_exit, base.risk_rules)
            name = f"{base.name}[mut_tp={tp}]"
            mutations.append(StrategyDef(
                strategy_key = key, name = name,
                entry_rules  = base.entry_rules,
                exit_rules   = new_exit,
                risk_rules   = base.risk_rules,
                generation   = base.generation + 1,
                origin       = "MUTATED",
                parent_ids   = [base.strategy_key],
            ))

        # Mutar SL multiplier
        for sl in SL_ATR_MULTS:
            if sl == base.exit_rules.get("stop_loss_atr_mult"):
                continue
            new_exit = dict(base.exit_rules)
            new_exit["stop_loss_atr_mult"] = sl
            key  = _make_key(base.entry_rules, new_exit, base.risk_rules)
            name = f"{base.name}[mut_sl={sl}]"
            mutations.append(StrategyDef(
                strategy_key = key, name = name,
                entry_rules  = base.entry_rules,
                exit_rules   = new_exit,
                risk_rules   = base.risk_rules,
                generation   = base.generation + 1,
                origin       = "MUTATED",
                parent_ids   = [base.strategy_key],
            ))

        # Mutar regime filter
        for regimes in REGIME_FILTERS:
            if regimes == base.risk_rules.get("regime_filter"):
                continue
            new_risk = dict(base.risk_rules)
            new_risk["regime_filter"] = regimes
            key  = _make_key(base.entry_rules, base.exit_rules, new_risk)
            name = f"{base.name}[mut_reg={'+'.join(regimes)}]"
            mutations.append(StrategyDef(
                strategy_key = key, name = name,
                entry_rules  = base.entry_rules,
                exit_rules   = base.exit_rules,
                risk_rules   = new_risk,
                generation   = base.generation + 1,
                origin       = "MUTATED",
                parent_ids   = [base.strategy_key],
            ))

        return mutations

    def crossover(self, a: StrategyDef, b: StrategyDef) -> StrategyDef:
        """
        Combina entry rules de A com exit/risk rules de B.
        Determinístico: resultado depende exclusivamente dos pais.
        """
        key  = _make_key(a.entry_rules, b.exit_rules, b.risk_rules)
        name = f"CROSS[{a.name[:30]}×{b.name[:30]}]"
        return StrategyDef(
            strategy_key = key,
            name         = name,
            entry_rules  = a.entry_rules,
            exit_rules   = b.exit_rules,
            risk_rules   = b.risk_rules,
            generation   = max(a.generation, b.generation) + 1,
            origin       = "CROSSOVER",
            parent_ids   = [a.strategy_key, b.strategy_key],
        )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_coherent(criteria: list[str]) -> bool:
    """Filtra combinações incoerentes (ex: bullish + bearish ao mesmo tempo)."""
    has_bull  = "macd_bullish" in criteria or "ema_trend_up"   in criteria
    has_bear  = "macd_bearish" in criteria or "ema_trend_down" in criteria
    has_fear  = "fear_extreme" in criteria
    has_greed = "greed_extreme" in criteria
    has_rsi_os = "rsi_oversold" in criteria
    has_rsi_ob = "rsi_overbought" in criteria

    if has_bull and has_bear: return False
    if has_fear and has_greed: return False
    if has_rsi_os and has_rsi_ob: return False
    return True


def _build_entry(criteria: list[str]) -> dict:
    """Constrói entry_rules JSON a partir da lista de critérios."""
    d: dict[str, Any] = {c: True for c in criteria}
    # Parâmetros quantitativos padrão (os melhores do Alpha Discovery)
    if "rsi_oversold"  in criteria: d["rsi_threshold"] = 30
    if "rsi_overbought" in criteria: d["rsi_threshold"] = 70
    if "ema_trend_up" in criteria or "ema_trend_down" in criteria:
        d["ema_fast"] = 20
        d["ema_slow"] = 50
    if "context_bullish" in criteria:
        d["context_score_min"] = 60
    return d


def _build_exit(tp: float, sl: float, hold: int) -> dict:
    return {
        "take_profit_atr_mult": tp,
        "stop_loss_atr_mult":   sl,
        "max_hold_candles":     hold,
        "risk_reward_ratio":    round(tp / sl, 2),
    }


def _build_risk(conf: int, regimes: list[str]) -> dict:
    return {
        "min_confluence":  conf,
        "regime_filter":   regimes,
        "max_drawdown_pct": 20.0,
        "candidate_only":  True,   # nunca substitui estratégia ativa automaticamente
    }


def _make_key(entry: dict, exit_r: dict, risk: dict) -> str:
    """Hash SHA-256 determinístico dos parâmetros da estratégia."""
    payload = json.dumps({"e": entry, "x": exit_r, "r": risk}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _make_name(criteria: list[str], tp: float, sl: float, regimes: list[str]) -> str:
    short = {
        "rsi_oversold": "RSI_OS", "rsi_overbought": "RSI_OB",
        "macd_bullish": "MACD+",  "macd_bearish":   "MACD-",
        "ema_trend_up": "EMA+",   "ema_trend_down":  "EMA-",
        "bos_detected": "BOS",    "choch_detected":  "CHOC",
        "fvg_present":  "FVG",    "sweep_present":   "SWP",
        "hvn_support":  "HVN",    "fear_extreme":    "FEAR",
        "greed_extreme":"GREED",  "funding_negative":"FUND-",
        "oi_increasing":"OI+",    "context_bullish": "CTX+",
    }
    crit_str   = "+".join(short.get(c, c[:4]) for c in criteria)
    reg_str    = "ALL" if len(regimes) >= 4 else "+".join(r[:3] for r in regimes)
    return f"S[{crit_str}|TP{tp}×SL{sl}|{reg_str}]"


# ── Singleton ─────────────────────────────────────────────────────────────────

strategy_generator = StrategyGenerator()
