"""
TradeAI - Endpoints: Market Context (Fase 5)

Rotas HTTP:
  GET /api/v1/context/news              → notícias recentes (filtro por ativo)
  GET /api/v1/context/news/sentiment    → resumo de sentimento
  GET /api/v1/context/fear-greed        → último Fear & Greed
  GET /api/v1/context/fear-greed/history→ histórico F&G
  GET /api/v1/context/funding           → funding rates atuais por símbolo
  GET /api/v1/context/open-interest     → OI atual por símbolo
  GET /api/v1/context/score             → Market Context Score completo
"""

from fastapi import APIRouter, Query
from app.schemas.market_context import (
    NewsArticleResponse,
    NewsSentimentSummary,
    FearGreedResponse,
    FundingRateResponse,
    OpenInterestResponse,
    ContextScoreResponse,
    NewsBreakdown,
)
from app.services.news.news_store                import news_store
from app.services.market_context.fear_greed      import fear_greed_service
from app.services.market_context.funding_rate    import funding_rate_service
from app.services.market_context.open_interest   import open_interest_service
from app.services.market_context.context_engine  import context_engine
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


# ── Notícias ──────────────────────────────────────────────────────────────────

@router.get(
    "/news",
    response_model=list[NewsArticleResponse],
    summary="Notícias recentes de mercado cripto",
)
async def get_news(
    asset: str = Query("ALL", description="BTC | ETH | SOL | GENERAL | ALL"),
    limit: int = Query(20,    ge=1, le=100),
    hours: int = Query(48,    ge=1, le=720),
) -> list[NewsArticleResponse]:
    articles = await news_store.get_recent(
        asset=None if asset.upper() == "ALL" else asset,
        limit=limit,
        hours=hours,
    )
    return [NewsArticleResponse.model_validate(a) for a in articles]


@router.get(
    "/news/sentiment",
    response_model=NewsSentimentSummary,
    summary="Resumo de sentimento das notícias",
)
async def get_news_sentiment(
    asset: str = Query("ALL", description="BTC | ETH | SOL | ALL"),
    hours: int = Query(24,    ge=1, le=168),
) -> NewsSentimentSummary:
    summary = await news_store.get_sentiment_summary(
        asset=None if asset.upper() == "ALL" else asset,
        hours=hours,
    )
    return NewsSentimentSummary(**summary)


# ── Fear & Greed ──────────────────────────────────────────────────────────────

@router.get(
    "/fear-greed",
    response_model=FearGreedResponse | None,
    summary="Índice Fear & Greed atual",
)
async def get_fear_greed() -> FearGreedResponse | None:
    fg = await fear_greed_service.get_latest()
    if fg is None:
        return None
    return FearGreedResponse.model_validate(fg)


@router.get(
    "/fear-greed/history",
    response_model=list[FearGreedResponse],
    summary="Histórico Fear & Greed",
)
async def get_fear_greed_history(
    limit: int = Query(30, ge=1, le=100),
) -> list[FearGreedResponse]:
    history = await fear_greed_service.get_history(limit=limit)
    return [FearGreedResponse.model_validate(fg) for fg in history]


# ── Funding Rate ──────────────────────────────────────────────────────────────

@router.get(
    "/funding",
    response_model=list[FundingRateResponse],
    summary="Funding rates atuais (BTC, ETH, SOL)",
)
async def get_funding_rates() -> list[FundingRateResponse]:
    rates = await funding_rate_service.get_all_latest()
    return [FundingRateResponse.model_validate(r) for r in rates]


# ── Open Interest ─────────────────────────────────────────────────────────────

@router.get(
    "/open-interest",
    response_model=list[OpenInterestResponse],
    summary="Open Interest atual (BTC, ETH, SOL)",
)
async def get_open_interest() -> list[OpenInterestResponse]:
    ois = await open_interest_service.get_all_latest()
    return [OpenInterestResponse.model_validate(oi) for oi in ois]


@router.get(
    "/open-interest/history",
    response_model=list[OpenInterestResponse],
    summary="Histórico de Open Interest por símbolo",
)
async def get_oi_history(
    symbol: str = Query("BTCUSDT"),
    limit:  int = Query(24, ge=1, le=100),
) -> list[OpenInterestResponse]:
    history = await open_interest_service.get_history(symbol.upper(), limit=limit)
    return [OpenInterestResponse.model_validate(oi) for oi in history]


# ── Context Score ─────────────────────────────────────────────────────────────

@router.get(
    "/score",
    response_model=ContextScoreResponse,
    summary="Market Context Score agregado (0-100)",
)
async def get_context_score(
    symbol: str = Query("BTCUSDT", description="BTCUSDT | ETHUSDT | SOLUSDT"),
) -> ContextScoreResponse:
    ctx = await context_engine.calculate(symbol.upper())
    return ContextScoreResponse(
        symbol           = ctx.symbol,
        news_score       = ctx.news_score,
        fear_greed       = ctx.fear_greed,
        fear_greed_label = ctx.fear_greed_label,
        funding_score    = ctx.funding_score,
        funding_label    = ctx.funding_label,
        oi_score         = ctx.oi_score,
        oi_change_pct    = ctx.oi_change_pct,
        context_score    = ctx.context_score,
        context_label    = ctx.context_label,
        news_sentiment   = NewsBreakdown(**ctx.news_sentiment),
    )
