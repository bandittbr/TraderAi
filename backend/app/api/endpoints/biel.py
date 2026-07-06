"""
Biel — Endpoints API
Gerenciamento do agente Biel: configuração, posts, tokens.
"""

import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from pathlib import Path
import httpx

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
    reels_per_day: int = 2
    reel_hours: str = "9,21"
    instagram_account_id: str | None = None  # se fornecido, pula auto-detecção
    music_url: str | None = None  # URL de música para reels


class PostRequest(BaseModel):
    topic: str | None = None      # "market" | "trade" | "insight" | "news" | tópico de reel
    post_type: str | None = None  # "image" | "reel" (auto se None)


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
            instagram_account_id_override=data.instagram_account_id,
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
                reels_per_day       = data.reels_per_day,
                reel_hours          = data.reel_hours,
                music_url           = data.music_url,
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
            "reel_hours": config.reel_hours if config else None,
            "reels_per_day": config.reels_per_day if config else 0,
            "instagram_account_id": config.instagram_account_id if config else None,
            "token_active": token is not None and token.is_active,
            "token_expires_at": token.expires_at.isoformat() if (token and token.expires_at) else None,
            "recent_posts": [
                {
                    "id": p.id,
                    "post_type": p.post_type,
                    "topic": p.topic,
                    "reel_topic": p.reel_topic,
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
    """Força um post manual imediato (imagem ou reel)."""
    result = await run_post(topic=data.topic, post_type=data.post_type)
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


# ── Verificar token atual contra Facebook API ─────────────────────────────────

@router.get("/token/verify")
async def verify_token():
    """
    Verifica se o token armazenado no banco é válido consultando a Facebook API.
    Retorna info do usuário ou erro detalhado.
    """
    token = await get_active_token()
    if not token:
        return {"valid": False, "error": "Nenhum token no banco", "stored_prefix": None}

    stored_prefix = token.access_token[:20] + "..." if token.access_token else None

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://graph.facebook.com/v19.0/me",
                params={
                    "access_token": token.access_token,
                    "fields": "id,name",
                }
            )
            data = resp.json()
            if resp.is_success and "id" in data:
                return {
                    "valid": True,
                    "user_id": data.get("id"),
                    "user_name": data.get("name"),
                    "stored_prefix": stored_prefix,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                    "account_id": token.account_id,
                }
            else:
                err = data.get("error", {})
                return {
                    "valid": False,
                    "error": err.get("message", resp.text),
                    "error_code": err.get("code"),
                    "stored_prefix": stored_prefix,
                    "expires_at": token.expires_at.isoformat() if token.expires_at else None,
                }
    except Exception as e:
        return {"valid": False, "error": str(e), "stored_prefix": stored_prefix}





# ── Atualizar apenas o token (sem refazer setup completo) ─────────────────────

class TokenUpdateRequest(BaseModel):
    access_token: str
    app_id: str | None = None
    app_secret: str | None = None


@router.post("/token/update")
async def update_token(data: TokenUpdateRequest):
    """
    Atualiza apenas o access token no banco, sem refazer o setup completo.
    Tenta converter para long-lived se app_id e app_secret forem fornecidos.
    Útil quando o token expirou mas o restante da configuração está OK.
    """
    token = await get_active_token()
    if not token:
        raise HTTPException(status_code=404, detail="Nenhum token configurado. Use /biel/setup primeiro.")

    now = datetime.now(timezone.utc)
    new_token_str = data.access_token
    expires_at = now + timedelta(days=60)

    # Tentar trocar por long-lived se credenciais fornecidas
    app_id     = data.app_id     or token.app_id
    app_secret = data.app_secret or token.app_secret

    if app_id and app_secret:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    "https://graph.facebook.com/v19.0/oauth/access_token",
                    params={
                        "grant_type":        "fb_exchange_token",
                        "client_id":         app_id,
                        "client_secret":     app_secret,
                        "fb_exchange_token": data.access_token,
                    }
                )
                if resp.is_success:
                    ex_data    = resp.json()
                    new_token_str = ex_data.get("access_token", data.access_token)
                    expires_in    = ex_data.get("expires_in", 5183944)
                    expires_at    = now + timedelta(seconds=expires_in)
                    logger.info(f"[biel/api] Token trocado por long-lived. Expira: {expires_at.date()}")
                else:
                    logger.warning(f"[biel/api] Exchange falhou ({resp.status_code}): {resp.text}. Usando token direto.")
        except Exception as e:
            logger.warning(f"[biel/api] Exchange exception: {e}. Usando token direto.")

    async with AsyncSessionLocal() as session:
        db_token = await session.get(BielToken, token.id)
        db_token.access_token    = new_token_str
        db_token.expires_at      = expires_at
        db_token.last_renewed_at = now
        db_token.is_active       = True
        if app_id:     db_token.app_id     = app_id
        if app_secret: db_token.app_secret = app_secret
        await session.commit()

    logger.info(f"[biel/api] Token atualizado. Expira: {expires_at.date()}")
    return {
        "status": "ok",
        "token_prefix": new_token_str[:20] + "...",
        "expires_at": expires_at.isoformat(),
        "account_id": token.account_id,
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
                "post_type": p.post_type,
                "topic": p.topic,
                "reel_topic": p.reel_topic,
                "status": p.status,
                "instagram_id": p.instagram_id,
                "caption": p.caption,
                "image_path": p.image_path,
                "video_path": p.video_path,
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


# ── Métricas completas (Influencer Dashboard) ─────────────────────────────────

@router.get("/metrics")
async def get_metrics():
    """
    Métricas completas do Biel para o painel Influencer.
    Inclui: posts por período, por tópico, próximo post, agenda do dia.
    """
    from datetime import date

    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    async with AsyncSessionLocal() as session:

        # Configuração ativa
        config_result = await session.execute(
            select(BielConfig).where(BielConfig.is_active == True).limit(1)
        )
        config = config_result.scalar_one_or_none()

        # Token ativo
        token = await get_active_token()

        # Totais gerais
        total_q = await session.execute(select(func.count(BielPost.id)))
        pub_q   = await session.execute(select(func.count(BielPost.id)).where(BielPost.status == "published"))
        fail_q  = await session.execute(select(func.count(BielPost.id)).where(BielPost.status == "failed"))

        # Posts de hoje (publicados)
        today_q = await session.execute(
            select(func.count(BielPost.id)).where(
                BielPost.status == "published",
                BielPost.published_at >= datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
            )
        )

        # Posts desta semana
        week_q = await session.execute(
            select(func.count(BielPost.id)).where(
                BielPost.status == "published",
                BielPost.published_at >= datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
            )
        )

        # Posts deste mês
        month_q = await session.execute(
            select(func.count(BielPost.id)).where(
                BielPost.status == "published",
                BielPost.published_at >= datetime(month_start.year, month_start.month, month_start.day, tzinfo=timezone.utc)
            )
        )

        # Breakdown por tópico (imagens)
        topics_q = await session.execute(
            select(BielPost.topic, func.count(BielPost.id))
            .where(BielPost.status == "published", BielPost.post_type == "image")
            .group_by(BielPost.topic)
        )
        topics = {row[0]: row[1] for row in topics_q.all()}

        # Breakdown por tópico de reels
        reel_topics_q = await session.execute(
            select(BielPost.reel_topic, func.count(BielPost.id))
            .where(BielPost.status == "published", BielPost.post_type == "reel")
            .group_by(BielPost.reel_topic)
        )
        reel_topics = {row[0]: row[1] for row in reel_topics_q.all()}

        # Contagem de reels publicados
        reels_published_q = await session.execute(
            select(func.count(BielPost.id)).where(
                BielPost.status == "published",
                BielPost.post_type == "reel",
            )
        )
        reels_published = reels_published_q.scalar()

        # Último post publicado
        last_q = await session.execute(
            select(BielPost)
            .where(BielPost.status == "published")
            .order_by(desc(BielPost.published_at))
            .limit(1)
        )
        last_post = last_q.scalar_one_or_none()

        # Posts por dia (últimos 7 dias)
        daily = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            d_start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
            d_end   = d_start + timedelta(days=1)
            cnt_q = await session.execute(
                select(func.count(BielPost.id)).where(
                    BielPost.status == "published",
                    BielPost.published_at >= d_start,
                    BielPost.published_at < d_end,
                )
            )
            daily.append({"date": d.isoformat(), "count": cnt_q.scalar()})

        # Agenda do dia — quais slots já foram postados hoje
        post_hours = []
        schedule_slots = []
        if config:
            try:
                post_hours = [int(h.strip()) for h in config.post_hours.split(",")]
            except Exception:
                post_hours = [8, 12, 18, 22]

            for h in post_hours:
                slot_start = datetime(today.year, today.month, today.day, h, 0, 0, tzinfo=timezone.utc)
                slot_end   = slot_start + timedelta(hours=1)
                slot_q = await session.execute(
                    select(func.count(BielPost.id)).where(
                        BielPost.published_at >= slot_start,
                        BielPost.published_at < slot_end,
                    )
                )
                done = slot_q.scalar() > 0
                schedule_slots.append({
                    "hour": h,
                    "label": f"{h:02d}:00 UTC",
                    "done": done,
                    "is_next": not done and slot_start > now,
                    "is_past": slot_start <= now and not done,
                })

        # Próximo post
        next_post_in_minutes = None
        next_post_label = None
        for slot in schedule_slots:
            if not slot["done"] and not slot["is_past"]:
                slot_dt = datetime(today.year, today.month, today.day, slot["hour"], 0, 0, tzinfo=timezone.utc)
                diff = int((slot_dt - now).total_seconds() / 60)
                next_post_in_minutes = diff
                h = slot["hour"]
                next_post_label = f"{h:02d}:00 UTC"
                break

        # Taxa de sucesso
        total_val = total_q.scalar() or 0
        pub_val   = pub_q.scalar() or 0
        success_rate = round(pub_val / total_val * 100) if total_val > 0 else 0

        # Dias ativos (desde o primeiro post)
        first_q = await session.execute(
            select(BielPost.created_at).order_by(BielPost.created_at).limit(1)
        )
        first_post = first_q.scalar_one_or_none()
        days_active = (now.date() - first_post.date()).days + 1 if first_post else 0

        return {
            "status": {
                "configured": config is not None,
                "active": config.is_active if config else False,
                "token_active": token is not None and token.is_active,
                "token_expires_at": token.expires_at.isoformat() if (token and token.expires_at) else None,
                "token_days_left": (token.expires_at.date() - today).days if (token and token.expires_at) else None,
                "instagram_account_id": config.instagram_account_id if config else None,
                "posts_per_day": config.posts_per_day if config else 0,
                "post_hours": config.post_hours if config else None,
                "reels_per_day": config.reels_per_day if config else 0,
                "reel_hours": config.reel_hours if config else None,
                "persona_name": config.persona_name if config else "Biel",
            },
            "counters": {
                "total": total_val,
                "published": pub_val,
                "failed": fail_q.scalar(),
                "today": today_q.scalar(),
                "week": week_q.scalar(),
                "month": month_q.scalar(),
                "success_rate": success_rate,
                "days_active": days_active,
                "reels_published": reels_published,
            },
            "topics": topics,
            "reel_topics": reel_topics,
            "schedule": {
                "slots": schedule_slots,
                "next_post_in_minutes": next_post_in_minutes,
                "next_post_label": next_post_label,
            },
            "daily": daily,
            "last_post": {
                "topic": last_post.topic,
                "caption_preview": (last_post.caption[:100] + "...") if last_post and last_post.caption and len(last_post.caption) > 100 else (last_post.caption if last_post else None),
                "instagram_id": last_post.instagram_id if last_post else None,
                "published_at": last_post.published_at.isoformat() if last_post and last_post.published_at else None,
                "regime": last_post.regime if last_post else None,
                "pnl_snapshot": last_post.pnl_snapshot if last_post else None,
            } if last_post else None,
        }
