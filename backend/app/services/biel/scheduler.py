"""
Biel — Scheduler
Agenda posts automáticos nos horários configurados (padrão: 8, 12, 18, 22).
Roda como background task junto com o servidor FastAPI.
"""

import asyncio
from datetime import datetime, timezone

from app.services.biel.post_engine import run_post, _get_config
from app.services.biel.token_manager import check_and_renew
from app.logger import get_logger

logger = get_logger(__name__)


async def _should_post_now(config, now: datetime) -> bool:
    """Verifica se a hora atual é um dos horários configurados."""
    try:
        hours = [int(h.strip()) for h in config.post_hours.split(",")]
    except Exception:
        hours = [8, 12, 18, 22]
    return now.hour in hours


async def biel_scheduler_loop():
    """
    Loop principal do Biel — verifica a cada minuto se é hora de postar.
    Só posta uma vez por hora (controla via set de horas já postadas).
    """
    logger.info("[biel/scheduler] Iniciado")
    posted_hours: set = set()
    last_token_check_day: int = -1

    while True:
        try:
            now = datetime.now(timezone.utc)

            # Renovação diária do token (roda uma vez por dia)
            if now.day != last_token_check_day:
                await check_and_renew()
                last_token_check_day = now.day
                logger.info("[biel/scheduler] Verificação de token executada")

            # Reset de horas postadas a cada dia
            day_key = now.strftime("%Y-%m-%d")
            posted_keys = {k for k in posted_hours if k.startswith(day_key)}
            if len(posted_keys) != len(posted_hours):
                posted_hours = posted_keys

            # Verificar se é hora de postar
            config = await _get_config()
            if config and config.is_active:
                hour_key = f"{day_key}-{now.hour}"
                if hour_key not in posted_hours:
                    if await _should_post_now(config, now):
                        logger.info(f"[biel/scheduler] Hora de postar! {now.strftime('%H:%M UTC')}")
                        result = await run_post()
                        posted_hours.add(hour_key)
                        logger.info(f"[biel/scheduler] Resultado: {result.get('status')}")

        except Exception as e:
            logger.error(f"[biel/scheduler] Erro no loop: {e}")

        await asyncio.sleep(60)  # Verifica a cada minuto


async def start_biel_scheduler() -> list:
    """Inicia o scheduler do Biel como background task."""
    task = asyncio.create_task(biel_scheduler_loop())
    logger.info("[biel/scheduler] Background task criada")
    return [task]
