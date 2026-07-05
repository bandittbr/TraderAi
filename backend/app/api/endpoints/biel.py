"""
Biel — Endpoints API
Gerenciamento do agente Biel: configuração, posts, tokens.
"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from pathlib import Path

from app.database import AsyncSessionLocal
from app.models.biel import BielPost, BielToken, BielConfig
from app.services.biel.post_engine import run_post
from app.services.biel.token_manager import save_initial_token, check_and_renew, get_active_token
from app.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

IMAGES_DIR = Path("data/biel_images")


# ── Schemas ───────────────────────────────────────────────────────────────────

class SetupRequest(BaseModel):
    gemini_api_key: str
    access_token: str
    app_id: str
    app_secret: str
    posts_per_day: int = 4
    post_hours: str = "8,12,18,22"


class PostRequest(BaseModel):
    topic: str | None = None  # "market" | "trade" | "insight" | "news"


# ── Imagens estáticas ─────────────────────────────────────────────────────────

@router.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve imagens geradas para o Instagram."""
    filepath = IMAGES_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Imagem não encontrada")
    return FileResponse(str(filepath), media_type="image/png")


# ── Setup inicial ─────────────────────────────────────────────────────────────

@router.post("/setup")
async def setup_biel(data: SetupRequest):
    """
    Configura o Biel pela primeira vez.
    Salva token Instagram (já converte para long-lived) e configurações.
    """
    try:
        # Salvar token Instagram
        token = await save_initial_token(
            access_token=data.access_token,
            app_id=data.app_id,
            app_secret=data.app_secret,
        )

        ig_account_id = token.account_id

        # Salvar configuração
        async with AsyncSessionLocal() as session:
            # Desativar configurações anteriores
            existing = await session.execute(select(BielConfig))
            for cfg in existing.scalars().all():
                cfg.is_active = False

            new_config = BielConfig(
                gemini_api_key      = data.gemini_api_key,
                posts_per_day       = data.posts_per_day,
                post_hours          = data.post_hours,
                is_active           = True,
                instagram_account_id = ig_account_id,
            )
            session.add(new_config)
            await session.commit()

        return {
            "status": "ok",
            "instagram_account_id": ig_account_id,
            "token_expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "post_hours": data.post_hours,
        }
    except Exception as e:
        logger.error(f"[biel/api] Erro no setup: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── Status do Biel ────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Retorna o status atual do Biel."""
    async with AsyncSessionLocal() as session:
        config_result = await session.execute(
            select(BielConfig).where(BielConfig.is_active == True).limit(1)
        )
        config = config_result.scalar_one_or_none()

        token = await get_active_token()

        posts_result = await session.execute(
            select(BielPost)
            .order_by(desc(BielPost.created_at))
            .limit(10)
        )
        posts = posts_result.scalars().all()

        return {
            "configured": config is not None,
            "active": config.is_active if config else False,
            "post_hours": config.post_hours if config else None,
            "posts_per_day": config.posts_per_day if config else 0,
            "instagram_account_id": config.instagram_account_id if config else None,
            "token_active": token is not None and token.is_active,
            "token_expires_at": token.expires_at.isoformat() if (token and token.expires_at) else None,
            "recent_posts": [
                {
                    "id": p.id,
                    "topic": p.topic,
                    "status": p.status,
                    "instagram_id": p.instagram_id,
                    "caption_preview": (p.caption[:80] + "...") if p.caption and len(p.caption) > 80 else p.caption,
                    "published_at": p.published_at.isoformat() if p.published_at else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "error": p.error_msg,
                }
                for p in posts
            ],
        }


# ── Forçar post manual ────────────────────────────────────────────────────────

@router.post("/post")
async def force_post(data: PostRequest = PostRequest()):
    """Força um post manual imediato."""
    result = await run_post(topic=data.topic)
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


# ── Renovar token manualmente ─────────────────────────────────────────────────

@router.post("/token/renew")
async def renew_token():
    """Força renovação manual do token Instagram."""
    await check_and_renew()
    token = await get_active_token()
    return {
        "status": "ok",
        "expires_at": token.expires_at.isoformat() if (token and token.expires_at) else None,
    }


# ── Histórico de posts ────────────────────────────────────────────────────────

@router.get("/posts")
async def list_posts(limit: int = 50):
    """Lista posts com histórico."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BielPost)
            .order_by(desc(BielPost.created_at))
            .limit(limit)
        )
        posts = result.scalars().all()
        return [
            {
                "id": p.id,
                "topic": p.topic,
                "status": p.status,
                "instagram_id": p.instagram_id,
                "caption": p.caption,
                "image_path": p.image_path,
                "regime": p.regime,
                "pnl_snapshot": p.pnl_snapshot,
                "error": p.error_msg,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in posts
        ]


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Retorna estatísticas de publicação."""
    from sqlalchemy import func
    async with AsyncSessionLocal() as session:
        total = await session.execute(select(func.count(BielPost.id)))
        published = await session.execute(
            select(func.count(BielPost.id)).where(BielPost.status == "published")
        )
        failed = await session.execute(
            select(func.count(BielPost.id)).where(BielPost.status == "failed")
        )
        return {
            "total": total.scalar(),
            "published": published.scalar(),
            "failed": failed.scalar(),
        }
