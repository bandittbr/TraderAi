"""
TradeAI - News Analyzer (Fase 5)
Classificação de sentimento e impacto por regras — sem IA, sem LLM.

Lógica:
  1. Detecta ativo mencionado (BTC, ETH, SOL, ou GENERAL)
  2. Detecta categoria (REGULATION, ADOPTION, TECH, SECURITY, MACRO, NEWS)
  3. Calcula sentiment: POSITIVE / NEUTRAL / NEGATIVE por contagem de keywords
  4. Calcula impact_score 0-100 por presença de termos de alto impacto
"""

from __future__ import annotations
import re

# ── Dicionários de keywords ───────────────────────────────────────────────────

POSITIVE_KEYWORDS = {
    # Mercado
    "surge", "rally", "bull", "bullish", "soar", "skyrocket", "ath", "all-time high",
    "record", "gain", "pump", "moon", "breakout", "recovery", "rebound",
    # Adoção / institucional
    "approved", "approval", "etf", "launch", "partnership", "adoption", "institutional",
    "invest", "investment", "buy", "accumulate", "support", "backing", "funding",
    # Regulação positiva
    "legal", "regulate", "clarity", "framework", "compliance",
    # Tecnologia
    "upgrade", "improvement", "integration", "milestone", "mainnet",
    # Específico cripto
    "halving", "staking", "yield", "defi", "nft boom", "listing",
}

NEGATIVE_KEYWORDS = {
    # Mercado
    "crash", "dump", "bear", "bearish", "plunge", "collapse", "tank", "decline",
    "drop", "fall", "sell-off", "selloff", "correction", "liquidation", "loss",
    # Regulação negativa
    "ban", "banned", "crackdown", "restriction", "lawsuit", "sec", "fine",
    "penalty", "illegal", "sanction", "probe", "investigation",
    # Segurança
    "hack", "hacked", "exploit", "vulnerability", "breach", "scam", "fraud",
    "rug pull", "rugpull", "ponzi", "theft", "stolen",
    # Macro
    "recession", "inflation", "rate hike", "tightening",
    # Sentimento negativo
    "fear", "panic", "fud", "uncertainty", "concern", "warning", "risk",
}

HIGH_IMPACT_KEYWORDS = {
    # Aprovações / grandes eventos
    "etf approved", "sec approved", "etf approval", "spot etf",
    "federal reserve", "inflation data", "interest rate",
    "halving", "hard fork",
    # Segurança
    "hack", "exploit", "hacked", "$", "million", "billion",
    # Regulação
    "ban", "banned", "crackdown", "sec", "cftc",
    # Institucional
    "blackrock", "fidelity", "jpmorgan", "goldman", "morgan stanley",
    "mastercard", "visa", "paypal", "tesla", "microsoft",
    # Macro
    "recession", "fed", "fomc",
}

LOW_IMPACT_KEYWORDS = {
    "maintenance", "scheduled", "routine", "update", "minor",
    "community", "meetup", "conference", "event", "webinar",
}

ASSET_PATTERNS = {
    "BTC":  [r"\bbtc\b", r"\bbitcoin\b"],
    "ETH":  [r"\beth\b", r"\bethereum\b"],
    "SOL":  [r"\bsol\b", r"\bsolana\b"],
    "BNB":  [r"\bbnb\b", r"\bbinance\b"],
    "CRYPTO": [r"\bcrypto\b", r"\bblockchain\b", r"\bdefi\b", r"\bnft\b", r"\bweb3\b"],
}

CATEGORY_PATTERNS = {
    "REGULATION": ["sec", "regulation", "ban", "legal", "law", "cftc", "compliance",
                   "sanction", "crackdown", "framework"],
    "SECURITY":   ["hack", "exploit", "vulnerability", "breach", "stolen", "scam",
                   "fraud", "rugpull", "rug pull"],
    "ADOPTION":   ["etf", "adoption", "institutional", "partnership", "invest",
                   "listing", "launch", "integration"],
    "TECH":       ["upgrade", "mainnet", "testnet", "protocol", "hard fork", "soft fork",
                   "layer", "l2", "zkp", "consensus"],
    "MACRO":      ["federal reserve", "fed", "inflation", "gdp", "interest rate",
                   "recession", "fomc", "cpi"],
}


# ── Funções de análise ────────────────────────────────────────────────────────

def detect_asset(text: str) -> str:
    """Retorna o ativo mais mencionado ou 'GENERAL'."""
    lower = text.lower()
    counts: dict[str, int] = {}
    for asset, patterns in ASSET_PATTERNS.items():
        count = sum(len(re.findall(p, lower)) for p in patterns)
        if count > 0:
            counts[asset] = count

    if not counts:
        return "GENERAL"
    # Prioriza BTC/ETH/SOL sobre CRYPTO
    for asset in ("BTC", "ETH", "SOL", "BNB"):
        if asset in counts:
            return asset
    return max(counts, key=counts.get)  # type: ignore[arg-type]


def detect_category(text: str) -> str:
    """Classifica a notícia em uma categoria."""
    lower = text.lower()
    for category, keywords in CATEGORY_PATTERNS.items():
        if any(kw in lower for kw in keywords):
            return category
    return "NEWS"


def analyze_sentiment(title: str, summary: str = "") -> tuple[str, float]:
    """
    Retorna (sentiment, impact_score).
    Sentiment: POSITIVE | NEUTRAL | NEGATIVE
    Impact:    0-100 (float)
    """
    text = (title + " " + (summary or "")).lower()

    pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    # Determina sentimento por contagem
    if pos_count > neg_count:
        sentiment = "POSITIVE"
    elif neg_count > pos_count:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"

    # Impact score
    high_matches = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text)
    low_matches  = sum(1 for kw in LOW_IMPACT_KEYWORDS  if kw in text)

    base_score   = 40.0                          # base neutra
    keyword_bonus = min(high_matches * 15, 45)   # até +45 por termos de alto impacto
    keyword_penalty = min(low_matches * 10, 20)  # até -20 por termos de baixo impacto

    # Notícias positivas/negativas têm naturalmente mais impacto
    sentiment_bonus = 10.0 if sentiment != "NEUTRAL" else 0.0

    impact_score = base_score + keyword_bonus - keyword_penalty + sentiment_bonus
    impact_score = max(0.0, min(100.0, impact_score))

    return sentiment, round(impact_score, 1)


def analyze_article(title: str, summary: str = "") -> dict:
    """Retorna dict com todos os campos calculados para um artigo."""
    sentiment, impact = analyze_sentiment(title, summary)
    asset    = detect_asset(title + " " + summary)
    category = detect_category(title + " " + summary)
    return {
        "asset":        asset,
        "category":     category,
        "sentiment":    sentiment,
        "impact_score": impact,
    }
