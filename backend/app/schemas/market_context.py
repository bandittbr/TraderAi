"""
TradeAI - Schemas: Market Context (Fase 5)
Pydantic v2 — request/response para notícias, Fear & Greed, Funding, OI e Context Score.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ── Notícias ──────────────────────────────────────────────────────────────────

class NewsArticleResponse(BaseModel):
    id:           int
    source:       str
    title:        str
    summary:      Optional[str]
    url:          str
    published_at: datetime
    asset:        str
    category:     str
    sentiment:    str
    impact_score: float

    model_config = {"from_attributes": True}


class NewsSentimentSummary(BaseModel):
    positive:   int
    neutral:    int
    negative:   int
    total:      int
    avg_impact: float
    news_score: float    # 0-100


# ── Fear & Greed ──────────────────────────────────────────────────────────────

class FearGreedResponse(BaseModel):
    id:             int
    value:          int
    classification: str
    timestamp:      int
    created_at:     datetime

    model_config = {"from_attributes": True}


# ── Funding Rate ──────────────────────────────────────────────────────────────

class FundingRateResponse(BaseModel):
    id:           int
    symbol:       str
    rate:         float
    rate_percent: float
    sentiment:    str
    timestamp:    int
    created_at:   datetime

    model_config = {"from_attributes": True}


# ── Open Interest ─────────────────────────────────────────────────────────────

class OpenInterestResponse(BaseModel):
    id:                int
    symbol:            str
    open_interest:     float
    open_interest_usd: float
    timestamp:         int
    created_at:        datetime

    model_config = {"from_attributes": True}


# ── Context Score ─────────────────────────────────────────────────────────────

class NewsBreakdown(BaseModel):
    positive: int
    neutral:  int
    negative: int
    total:    int


class ContextScoreResponse(BaseModel):
    symbol:           str
    news_score:       float    = Field(description="Score de notícias 0-100")
    fear_greed:       float    = Field(description="Valor F&G 0-100")
    fear_greed_label: str
    funding_score:    float    = Field(description="Score de funding 0-100")
    funding_label:    str
    oi_score:         float    = Field(description="Score de OI 0-100")
    oi_change_pct:    Optional[float]
    context_score:    float    = Field(description="Score final 0-100")
    context_label:    str      = Field(description="Bearish | Neutral | Bullish")
    news_sentiment:   NewsBreakdown
