"""
TradeAI - News Store (Fase 5)
Persistência de notícias no banco SQLite.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.market_context import MarketNews
from app.services.news.news_fetcher import RawArticle
from app.logger import get_logger

logger = get_logger(__name__)


class NewsStore:

    async def save_articles(self, articles: list[RawArticle]) -> int:
        """
        Salva artigos no banco. Ignora duplicatas por URL.
        Retorna o número de novos artigos inseridos.
        """
        if not articles:
            return 0

        inserted = 0
        async with AsyncSessionLocal() as session:
            for art in articles:
                # Verifica duplicata por URL
                result = await session.execute(
                    select(MarketNews).where(MarketNews.url == art.url).limit(1)
                )
                if result.scalar_one_or_none():
                    continue

                session.add(MarketNews(
                    source       = art.source,
                    title        = art.title,
                    summary      = art.summary,
                    url          = art.url,
                    published_at = art.published_at,
                    asset        = art.asset,
                    category     = art.category,
                    sentiment    = art.sentiment,
                    impact_score = art.impact_score,
                ))
                inserted += 1

            await session.commit()

        return inserted

    async def get_recent(
        self,
        asset:  str | None = None,
        limit:  int = 20,
        hours:  int = 48,
    ) -> list[MarketNews]:
        """
        Retorna notícias recentes, opcionalmente filtradas por ativo.
        Ordenadas por data de publicação (mais recentes primeiro).
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        async with AsyncSessionLocal() as session:
            query = select(MarketNews).where(MarketNews.published_at >= cutoff)

            if asset and asset.upper() != "ALL":
                # Retorna notícias do ativo específico + notícias gerais de cripto
                query = query.where(
                    MarketNews.asset.in_([asset.upper(), "CRYPTO", "GENERAL"])
                )

            query = query.order_by(MarketNews.published_at.desc()).limit(limit)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_sentiment_summary(
        self, asset: str | None = None, hours: int = 24
    ) -> dict:
        """
        Resumo de sentimento das últimas N horas.
        Retorna: {positive, neutral, negative, avg_impact, news_score}
        """
        news = await self.get_recent(asset=asset, limit=100, hours=hours)

        if not news:
            return {
                "positive": 0, "neutral": 0, "negative": 0,
                "total": 0, "avg_impact": 50.0, "news_score": 50.0,
            }

        pos = sum(1 for n in news if n.sentiment == "POSITIVE")
        neg = sum(1 for n in news if n.sentiment == "NEGATIVE")
        neu = sum(1 for n in news if n.sentiment == "NEUTRAL")
        total = len(news)

        avg_impact = sum(n.impact_score for n in news) / total

        # News Score: weighted by sentiment and impact
        # Base: 50 neutro; positivas elevam, negativas reduzem
        sentiment_delta = (pos - neg) / total  # -1 a +1
        news_score = 50.0 + (sentiment_delta * 30) + ((avg_impact - 50) * 0.2)
        news_score = max(0.0, min(100.0, news_score))

        return {
            "positive":   pos,
            "neutral":    neu,
            "negative":   neg,
            "total":      total,
            "avg_impact": round(avg_impact, 1),
            "news_score": round(news_score, 1),
        }


# Singleton
news_store = NewsStore()
