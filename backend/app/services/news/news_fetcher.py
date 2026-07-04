"""
TradeAI - News Fetcher (Fase 5)
Coleta notícias de fontes RSS públicas via httpx.
Parse manual de XML com xml.etree.ElementTree (sem dependências extras).

Fontes:
  - CoinDesk RSS:      https://www.coindesk.com/arc/outboundfeeds/rss/
  - Cointelegraph RSS: https://cointelegraph.com/rss
  - Decrypt RSS:       https://decrypt.co/feed
  - Bitcoin Magazine:  https://bitcoinmagazine.com/feed
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from dataclasses import dataclass
from typing import Optional

import httpx

from app.services.news.news_analyzer import analyze_article
from app.logger import get_logger

logger = get_logger(__name__)


# ── Tipos ─────────────────────────────────────────────────────────────────────

@dataclass
class RawArticle:
    source:       str
    title:        str
    url:          str
    summary:      str
    published_at: datetime
    asset:        str
    category:     str
    sentiment:    str
    impact_score: float


# ── Fontes RSS ────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    {
        "name": "CoinDesk",
        "url":  "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "limit": 10,
    },
    {
        "name": "Cointelegraph",
        "url":  "https://cointelegraph.com/rss",
        "limit": 10,
    },
    {
        "name": "Decrypt",
        "url":  "https://decrypt.co/feed",
        "limit": 8,
    },
    {
        "name": "Bitcoin Magazine",
        "url":  "https://bitcoinmagazine.com/feed",
        "limit": 8,
    },
]

# Namespaces RSS/Atom
NS = {
    "dc":      "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media":   "http://search.yahoo.com/mrss/",
}

FETCH_TIMEOUT_SECS = 10


# ── Funções de parse ──────────────────────────────────────────────────────────

def _parse_date(date_str: str | None) -> datetime:
    """Converte string de data RSS para datetime UTC."""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _strip_html(text: str) -> str:
    """Remove tags HTML simples do resumo."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:500]  # limita a 500 chars


def _parse_rss_feed(xml_content: str, source_name: str, limit: int) -> list[RawArticle]:
    """Parse XML RSS 2.0 e retorna lista de artigos."""
    articles: list[RawArticle] = []

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        logger.warning(f"[news] Erro ao parsear RSS {source_name}: {e}")
        return []

    # Suporta RSS 2.0 (channel/item) e Atom (entry)
    items = root.findall(".//item") or root.findall(".//entry")

    for item in items[:limit]:
        try:
            title = (
                item.findtext("title") or
                item.findtext("{http://www.w3.org/2005/Atom}title") or ""
            ).strip()

            url = (
                item.findtext("link") or
                (item.find("{http://www.w3.org/2005/Atom}link") or {}).get("href", "") or  # type: ignore[call-overload]
                ""
            ).strip()

            if not title or not url:
                continue

            raw_summary = (
                item.findtext("description") or
                item.findtext("{http://www.w3.org/2005/Atom}summary") or
                item.findtext(f"{{{NS['content']}}}encoded") or
                ""
            )
            summary = _strip_html(raw_summary)

            pub_str = (
                item.findtext("pubDate") or
                item.findtext("{http://www.w3.org/2005/Atom}published") or
                item.findtext(f"{{{NS['dc']}}}date") or
                None
            )
            published_at = _parse_date(pub_str)

            # Análise de sentimento e impacto
            analysis = analyze_article(title, summary)

            articles.append(RawArticle(
                source       = source_name,
                title        = title[:500],
                url          = url[:1000],
                summary      = summary,
                published_at = published_at,
                asset        = analysis["asset"],
                category     = analysis["category"],
                sentiment    = analysis["sentiment"],
                impact_score = analysis["impact_score"],
            ))

        except Exception as exc:
            logger.debug(f"[news] Erro ao processar item de {source_name}: {exc}")
            continue

    return articles


# ── Fetcher principal ─────────────────────────────────────────────────────────

class NewsFetcher:

    async def fetch_all(self) -> list[RawArticle]:
        """Busca todas as fontes RSS e retorna artigos classificados."""
        all_articles: list[RawArticle] = []

        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT_SECS,
            headers={"User-Agent": "TradeAI/1.0 RSS Reader"},
            follow_redirects=True,
        ) as client:
            for feed in RSS_FEEDS:
                articles = await self._fetch_feed(client, feed)
                all_articles.extend(articles)
                logger.debug(f"[news] {feed['name']}: {len(articles)} artigos")

        logger.info(f"[news] Total coletado: {len(all_articles)} artigos")
        return all_articles

    async def _fetch_feed(
        self, client: httpx.AsyncClient, feed: dict
    ) -> list[RawArticle]:
        try:
            response = await client.get(feed["url"])
            response.raise_for_status()
            return _parse_rss_feed(
                response.text, feed["name"], feed["limit"]
            )
        except httpx.HTTPStatusError as e:
            logger.warning(f"[news] HTTP {e.response.status_code} em {feed['name']}")
            return []
        except Exception as exc:
            logger.warning(f"[news] Falha ao buscar {feed['name']}: {exc}")
            return []


# Singleton
news_fetcher = NewsFetcher()
