"""
Biel — Post Engine
Orquestra o pipeline completo: contexto → Gemini → imagem → Instagram.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.biel import BielPost, BielConfig, BielToken
from app.services.biel.context_builder import build_context
from app.services.biel.brain import generate_post
from app.services.biel.visual_generator import generate_image
from app.services.biel.instagram import publish_image
from app.services.biel.token_manager import get_active_token
from app.logger import get_logger

logger = get_logger(__name__)

TOPICS = ["market", "trade", "insight", "news"]

# URL base pública do backend (Railway)
BACKEND_URL = os.environ.get("BACKEND_URL", "https://traderai-production-cfe4.up.railway.app")


def _get_topic_for_post_number(n: int) -> str:
    """Rotaciona tópicos: 0→market, 1→trade, 2→insight, 3→news."""
    return TOPICS[n % len(TOPICS)]


async def _get_config() -> BielConfig | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BielConfig).where(BielConfig.is_active == True).limit(1)
        )
        return result.scalar_one_or_none()


async def run_post(topic: str | None = None) -> dict:
    """
    Executa um ciclo completo de postagem.
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

    # Prioridade: config > token (config é sempre o mais recente/correto)
    ig_account_id = config.instagram_account_id
    if not ig_account_id or ig_account_id in ("unknown", "") or not ig_account_id.isdigit():
        ig_account_id = token.account_id
    if not ig_account_id or ig_account_id in ("unknown", "") or not ig_account_id.isdigit():
        return {"status": "error", "error": f"Instagram Account ID inválido: '{ig_account_id}'. Configure um ID numérico válido."}

    # Determinar tópico
    if not topic:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import func as sqlfunc
            count_result = await session.execute(
                select(sqlfunc.count(BielPost.id))
            )
            total = count_result.scalar() or 0
        topic = _get_topic_for_post_number(total)

    logger.info(f"[biel/engine] Iniciando post — tópico: {topic}")

    # Criar registro pendente
    post_record = BielPost(
        post_type="image",
        caption="",
        topic=topic,
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

        # 2. Gerar texto com Gemini
        caption = await generate_post(context, topic, config.gemini_api_key)
        logger.info(f"[biel/engine] Caption gerada ({len(caption)} chars)")

        # 3. Gerar imagem
        image_path = await generate_image(context, topic)
        filename = Path(image_path).name
        image_url = f"{BACKEND_URL}/biel/images/{filename}"
        logger.info(f"[biel/engine] Imagem: {image_url}")

        # 4. Publicar no Instagram
        instagram_id = await publish_image(
            image_url=image_url,
            caption=caption,
            ig_account_id=ig_account_id,
            access_token=token.access_token,
        )

        # 5. Atualizar registro como publicado
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            db_post = await session.get(BielPost, post_id_db)
            db_post.caption        = caption
            db_post.image_path     = image_path
            db_post.instagram_id   = instagram_id
            db_post.status         = "published"
            db_post.published_at   = now
            db_post.regime         = context.get("regime")
            db_post.pnl_snapshot   = context.get("pnl_total")
            await session.commit()

        logger.info(f"[biel/engine] Post publicado com sucesso! IG ID: {instagram_id}")
        return {
            "status": "published",
            "instagram_id": instagram_id,
            "topic": topic,
            "caption_preview": caption[:100],
        }

    except Exception as e:
        logger.error(f"[biel/engine] Erro ao publicar: {e}")
        async with AsyncSessionLocal() as session:
            db_post = await session.get(BielPost, post_id_db)
            if db_post:
                db_post.status    = "failed"
                db_post.error_msg = str(e)
                await session.commit()
        return {"status": "error", "error": str(e)}
