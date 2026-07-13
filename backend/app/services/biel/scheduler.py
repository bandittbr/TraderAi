"""
Biel — Scheduler
Agenda posts automáticos: imagens nos horários configurados, reels em horários separados.
Inclui sincronização periódica de métricas de engajamento do Instagram.
Roda como background task junto com o servidor FastAPI.
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select, func as sqlfunc

from app.database import AsyncSessionLocal
from app.models.biel import BielPost
from app.services.biel.post_engine import run_post, _get_config
from app.services.biel.token_manager import check_and_renew
from app.logger import get_logger

logger = get_logger(__name__)


async def _should_post_now(config, now: datetime, post_type: str) -> tuple[bool, str | None]:
    """
    Verifica se a hora atual corresponde a um horário de post.
    Retorna (deve_postar, tópico).
    """
    try:
        if post_type == "reel":
            hours = [int(h.strip()) for h in (config.reel_hours or "9,21").split(",")]
        else:
            hours = [int(h.strip()) for h in (config.post_hours or "8,12,18,22").split(",")]
    except Exception:
        hours = [8, 12, 18, 22] if post_type == "image" else [9, 21]

    return now.hour in hours


async def _already_posted_this_hour(post_type: str, now: datetime) -> bool:
    """
    Confere no banco (fonte da verdade) se já existe um post desse tipo
    criado nesta janela de hora. O set `posted_hours` do loop é só em
    memória do processo — reinicia toda vez que o backend reinicia (deploy,
    crash, etc.), então sozinho ele não evita re-postar depois de um
    restart que caia dentro do mesmo horário configurado. Essa checagem no
    banco é a que realmente evita o post duplicado.
    """
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(sqlfunc.count(BielPost.id)).where(
                BielPost.post_type == post_type,
                BielPost.status.in_(("pending", "published")),
                BielPost.created_at >= hour_start,
            )
        )
        return (result.scalar() or 0) > 0


async def _count_posts_today(post_type: str, now: datetime) -> int:
    """Conta quantos posts desse tipo já foram publicados hoje."""
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(sqlfunc.count(BielPost.id)).where(
                BielPost.post_type == post_type,
                BielPost.status.in_(("pending", "published")),
                BielPost.created_at >= day_start,
            )
        )
        return result.scalar() or 0


async def biel_scheduler_loop():
    """
    Loop principal do Biel — verifica a cada minuto se é hora de postar.
    Posta imagens e reels em horários distintos.
    A cada 6h: sincroniza métricas de engajamento e atualiza pesos adaptativos.
    """
    logger.info("[biel/scheduler] Iniciado")
    posted_hours: set = set()
    last_token_check_day: int = -1
    last_metrics_sync_hour: int = -1

    while True:
        try:
            now = datetime.now(timezone.utc)

            # Renovação diária do token
            if now.day != last_token_check_day:
                await check_and_renew()
                last_token_check_day = now.day
                logger.info("[biel/scheduler] Verificação de token executada")

            # ── Sincronização de métricas (a cada 6h) ───────────────────
            current_hour_key = now.strftime("%Y-%m-%d-%H")
            if now.hour % 6 == 0 and now.hour != last_metrics_sync_hour:
                last_metrics_sync_hour = now.hour
                try:
                    from app.services.biel.instagram_insights import sync_post_metrics
                    from app.services.biel.engagement_analyzer import update_topic_performance

                    synced = await sync_post_metrics(max_posts=20)
                    if synced > 0:
                        # After syncing metrics, recalculate topic performance
                        perf = await update_topic_performance()
                        logger.info(
                            f"[biel/scheduler] Métricas sincronizadas: {synced} posts, "
                            f"{len(perf)} tópicos atualizados"
                        )
                    else:
                        logger.debug("[biel/scheduler] Nenhuma métrica nova para sincronizar")
                except Exception as e:
                    logger.error(f"[biel/scheduler] Erro na sincronização de métricas: {e}")

            # Reset de horas postadas a cada dia
            day_key = now.strftime("%Y-%m-%d")
            posted_keys = {k for k in posted_hours if k.startswith(day_key)}
            if len(posted_keys) != len(posted_hours):
                posted_hours = posted_keys

            # Verificar se é hora de postar
            config = await _get_config()
            if config and config.is_active:
                hour_key_image = f"{day_key}-image-{now.hour}"
                hour_key_reel = f"{day_key}-reel-{now.hour}"

                # Imagem?
                if hour_key_image not in posted_hours:
                    if await _should_post_now(config, now, "image"):
                        # Verificar limite diário
                        max_images = config.posts_per_day or 4
                        posted_today = await _count_posts_today("image", now)
                        if posted_today >= max_images:
                            logger.debug(
                                f"[biel/scheduler] Limite de imagens atingido "
                                f"({posted_today}/{max_images})"
                            )
                        elif await _already_posted_this_hour("image", now):
                            # Já existe post dessa hora no banco (ex: processo
                            # reiniciou e o set em memória zerou) — só marca,
                            # não posta de novo.
                            posted_hours.add(hour_key_image)
                        else:
                            logger.info(
                                f"[biel/scheduler] Hora de postar IMAGEM! "
                                f"{now.strftime('%H:%M UTC')}"
                            )
                            result = await run_post(post_type="image")
                            posted_hours.add(hour_key_image)
                            logger.info(
                                f"[biel/scheduler] Resultado imagem: "
                                f"{result.get('status')}"
                            )

                # Reel?
                if hour_key_reel not in posted_hours:
                    if await _should_post_now(config, now, "reel"):
                        # Verificar limite diário
                        max_reels = config.reels_per_day or 2
                        posted_reels_today = await _count_posts_today("reel", now)
                        if posted_reels_today >= max_reels:
                            logger.debug(
                                f"[biel/scheduler] Limite de reels atingido "
                                f"({posted_reels_today}/{max_reels})"
                            )
                        elif await _already_posted_this_hour("reel", now):
                            posted_hours.add(hour_key_reel)
                        else:
                            logger.info(
                                f"[biel/scheduler] Hora de postar REEL! "
                                f"{now.strftime('%H:%M UTC')}"
                            )
                            result = await run_post(post_type="reel")
                            posted_hours.add(hour_key_reel)
                            logger.info(
                                f"[biel/scheduler] Resultado reel: "
                                f"{result.get('status')}"
                            )

        except Exception as e:
            logger.error(f"[biel/scheduler] Erro no loop: {e}")

        await asyncio.sleep(60)


async def start_biel_scheduler() -> list:
    """Inicia o scheduler do Biel como background task."""
    task = asyncio.create_task(biel_scheduler_loop())
    logger.info("[biel/scheduler] Background task criada")
    return [task]
