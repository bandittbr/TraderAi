"""
Biel — Post Engine
Orquestra o pipeline completo: contexto → IA → mídia (imagem/reel) → Instagram.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, func as sqlfunc

from app.database import AsyncSessionLocal
from app.models.biel import BielPost, BielConfig, BielToken
from app.services.biel.context_builder import build_context
from app.services.biel.brain import generate_post
from app.services.biel.visual_generator import generate_image
from app.services.biel.reel_generator import generate_reel, download_music, REEL_TOPICS
from app.services.biel.instagram import publish_media
from app.services.biel.token_manager import get_active_token
from app.logger import get_logger

logger = get_logger(__name__)

TOPICS = ["market", "trade", "insight", "news"]
REEL_TOPIC_KEYS = list(REEL_TOPICS.keys())

# URL base pública do backend — auto-detect:
_railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN") or os.environ.get("RAILWAY_STATIC_URL")
BACKEND_URL = os.environ.get("BACKEND_URL") or (
    f"https://{_railway_domain}" if _railway_domain else "http://localhost:8000"
)


def _get_topic_for_post_number(n: int) -> str:
    """Rotaciona tópicos de imagem: 0→market, 1→trade, 2→insight, 3→news."""
    return TOPICS[n % len(TOPICS)]


def _get_reel_topic_for_post_number(n: int) -> str:
    """Rotaciona tópicos de reel: 0→insight, 1→noticias, 2→profits, 3→erros, etc."""
    return REEL_TOPIC_KEYS[n % len(REEL_TOPIC_KEYS)]


async def _get_config() -> BielConfig | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BielConfig).where(BielConfig.is_active == True).limit(1)
        )
        return result.scalar_one_or_none()


async def run_post(
    topic: str | None = None,
    post_type: str | None = None,
) -> dict:
    """
    Executa um ciclo completo de postagem.
    
    Args:
        topic: Tópico específico (opcional — auto-determinado se None)
        post_type: "image" ou "reel" (opcional — auto-determinado se None)
    
    Retorna dict com resultado (status, post_id, error).
    """
    config = await _get_config()
    if not config:
        logger.error("[biel/engine] Nenhuma configuração ativa. Configure o Biel primeiro.")
        return {"status": "error", "error": "Configuração não encontrada"}

    token = await get_active_token()
    if not token:
        logger.error("[biel/engine] Nenhum token Instagram ativo.")
        return {"status": "error", "error": "Token Instagram não configurado"}

    # Prioridade: config > token para account_id
    ig_account_id = config.instagram_account_id
    if not ig_account_id or ig_account_id in ("unknown", "") or not ig_account_id.isdigit():
        ig_account_id = token.account_id
    if not ig_account_id or ig_account_id in ("unknown", "") or not ig_account_id.isdigit():
        return {
            "status": "error",
            "error": f"Instagram Account ID inválido: '{ig_account_id}'."
        }

    # Determinar tipo de post (se não especificado)
    if not post_type:
        async with AsyncSessionLocal() as session:
            total = await session.execute(select(sqlfunc.count(BielPost.id)))
            total_count = total.scalar() or 0
        # Alterna: 00,02,04,06 → imagem; 01,03,05 → reel
        post_type = "reel" if total_count % 4 in (1, 3) else "image"

    # Determinar tópico
    if not topic:
        async with AsyncSessionLocal() as session:
            count_result = await session.execute(select(sqlfunc.count(BielPost.id)))
            total = count_result.scalar() or 0

        if post_type == "reel":
            topic = _get_reel_topic_for_post_number(total)
        else:
            topic = _get_topic_for_post_number(total)

    logger.info(f"[biel/engine] Iniciando post — tipo: {post_type}, tópico: {topic}")

    # Criar registro pendente
    post_record = BielPost(
        post_type=post_type,
        caption="",
        topic=topic if post_type == "image" else None,
        reel_topic=topic if post_type == "reel" else None,
        status="pending",
    )
    async with AsyncSessionLocal() as session:
        session.add(post_record)
        await session.commit()
        await session.refresh(post_record)
        post_id_db = post_record.id

    try:
        # 1. Contexto
        context = await build_context()
        logger.info(f"[biel/engine] Contexto coletado: {list(context.keys())}")

        # 2. Gerar texto
        caption = await generate_post(context, topic, config.gemini_api_key)
        logger.info(f"[biel/engine] Caption gerada ({len(caption)} chars)")

        if post_type == "reel":
            # ── Pipeline REEL ─────────────────────────────────────────────
            # 3a. Gerar imagem base para o reel
            image_path = await generate_image(context, topic)
            logger.info(f"[biel/engine] Imagem base gerada: {image_path}")

            # 4a. Baixar música (se não tiver)
            music_path = await download_music(config.music_url if config.music_url else None)

            # 5a. Gerar vídeo reel
            video_path = await generate_reel(
                image_path=image_path,
                caption=caption,
                topic=topic,
                music_path=music_path,
                duration=15,  # 15s de reel
            )
            filename = Path(video_path).name
            media_url = f"{BACKEND_URL}/biel/reels/{filename}"
            logger.info(f"[biel/engine] Reel URL: {media_url}")

            # 6a. Publicar no Instagram como VIDEO
            instagram_id = await publish_media(
                media_url=media_url,
                caption=caption,
                ig_account_id=ig_account_id,
                access_token=token.access_token,
                media_type="VIDEO",
            )

        else:
            # ── Pipeline IMAGE ────────────────────────────────────────────
            # 3b. Gerar imagem
            image_path = await generate_image(context, topic)
            filename = Path(image_path).name
            media_url = f"{BACKEND_URL}/biel/images/{filename}"
            logger.info(f"[biel/engine] Image URL: {media_url}")

            # 4b. Publicar no Instagram como IMAGE
            instagram_id = await publish_media(
                media_url=media_url,
                caption=caption,
                ig_account_id=ig_account_id,
                access_token=token.access_token,
                media_type="IMAGE",
            )

        # 5. Atualizar registro como publicado
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            db_post = await session.get(BielPost, post_id_db)
            db_post.caption        = caption
            db_post.image_path     = image_path if post_type == "image" else image_path
            db_post.video_path     = video_path if post_type == "reel" else None
            db_post.instagram_id   = instagram_id
            db_post.status         = "published"
            db_post.published_at   = now
            db_post.regime         = context.get("regime")
            db_post.pnl_snapshot   = context.get("pnl_total")
            await session.commit()

        logger.info(
            f"[biel/engine] {post_type.upper()} publicado com sucesso! IG ID: {instagram_id}"
        )
        return {
            "status": "published",
            "instagram_id": instagram_id,
            "topic": topic,
            "post_type": post_type,
            "caption_preview": caption[:100],
        }

    except Exception as e:
        logger.error(f"[biel/engine] Erro ao publicar {post_type}: {e}")
        async with AsyncSessionLocal() as session:
            db_post = await session.get(BielPost, post_id_db)
            if db_post:
                db_post.status    = "failed"
                db_post.error_msg = str(e)
                await session.commit()
        return {"status": "error", "error": str(e)}
