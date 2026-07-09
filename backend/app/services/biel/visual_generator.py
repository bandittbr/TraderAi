"""
Biel — Visual Generator (v5)
Gera publicações profissionais 1080x1350 (4:5) para Instagram.
4 modelos com identidade visual própria: Mercado, Trade, Insights, Notícia.

Renderização via HTML+CSS (Playwright) — layout nítido, escalável, sem
edição de pixels. Os templates estão em templates/*.html e as variáveis
{{VAR}} são substituídas por dados reais do contexto (ver html_renderer.py
e biel/context_builder.py para a origem dos dados).
"""

import asyncio
from pathlib import Path

from app.logger import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = Path("data/biel_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_market_image(ctx: dict) -> str:
    """Publicação MERCADO — template templates/market_template.html."""
    from app.services.biel.html_renderer import fill_market_template, render_sync

    html = fill_market_template(ctx)
    return render_sync(html, "market")


def generate_trade_image(ctx: dict) -> str:
    """Publicação TRADE — template templates/trade_template.html."""
    from app.services.biel.html_renderer import fill_trade_template, render_sync

    html = fill_trade_template(ctx)
    return render_sync(html, "trade")


def generate_insight_image(ctx: dict) -> str:
    """Publicação INSIGHT — template templates/insight_template.html."""
    from app.services.biel.html_renderer import fill_insight_template, render_sync

    html = fill_insight_template(ctx)
    return render_sync(html, "insight")


def generate_news_image(ctx: dict) -> str:
    """Publicação NOTÍCIA — template templates/news_template.html."""
    from app.services.biel.html_renderer import fill_news_template, render_sync

    html = fill_news_template(ctx)
    return render_sync(html, "news")


# ═══════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════

async def generate_image(context: dict, topic: str) -> str:
    """Gera publicação conforme o tópico usando o modelo apropriado."""
    loop = asyncio.get_event_loop()
    if topic == "trade":
        return await loop.run_in_executor(None, generate_trade_image, context)
    elif topic == "insight":
        return await loop.run_in_executor(None, generate_insight_image, context)
    elif topic == "news":
        return await loop.run_in_executor(None, generate_news_image, context)
    else:
        return await loop.run_in_executor(None, generate_market_image, context)
