"""
Biel — Instagram Publisher
Publica posts no Instagram via Graph API.
A imagem deve ser acessível via URL pública (servida pelo backend via /biel/images/).
"""

import asyncio
import httpx
from app.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


async def _wait_container_ready(client: httpx.AsyncClient, container_id: str, access_token: str, max_wait: int = 30) -> None:
    """
    Aguarda o container de mídia ficar FINISHED (pronto para publicar).
    Instagram processa a imagem de forma assíncrona.
    """
    for attempt in range(max_wait):
        resp = await client.get(
            f"{GRAPH_URL}/{container_id}",
            params={"fields": "status_code", "access_token": access_token}
        )
        if resp.is_success:
            status = resp.json().get("status_code", "")
            logger.info(f"[biel/instagram] Container {container_id} status: {status} (tentativa {attempt+1})")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise ValueError(f"Instagram rejeitou o container: status ERROR. Verifique a imagem/caption.")
            if status == "EXPIRED":
                raise ValueError("Container expirou antes de ser publicado.")
        await asyncio.sleep(2)
    raise ValueError(f"Container não ficou FINISHED após {max_wait * 2}s. Última status: {status}")


async def publish_image(
    image_url: str,
    caption: str,
    ig_account_id: str,
    access_token: str,
) -> str:
    """
    Publica uma imagem no Instagram via URL pública.
    Fluxo: criar container → aguardar FINISHED → publicar container.
    Retorna o ID do post publicado.
    """
    async with httpx.AsyncClient(timeout=90.0) as client:

        # Passo 1: Criar container de mídia
        resp = await client.post(
            f"{GRAPH_URL}/{ig_account_id}/media",
            data={
                "image_url":    image_url,
                "caption":      caption,
                "access_token": access_token,
            }
        )
        if not resp.is_success:
            error_body = resp.text
            logger.error(f"[biel/instagram] Erro ao criar container: {resp.status_code} — {error_body}")
            raise ValueError(f"Instagram container error {resp.status_code}: {error_body}")
        container_id = resp.json().get("id")
        if not container_id:
            raise ValueError(f"Instagram não retornou container_id: {resp.text}")
        logger.info(f"[biel/instagram] Container criado: {container_id}")

        # Passo 2: Aguardar container ficar FINISHED
        await _wait_container_ready(client, container_id, access_token)

        # Passo 3: Publicar o container
        pub_resp = await client.post(
            f"{GRAPH_URL}/{ig_account_id}/media_publish",
            data={
                "creation_id":  container_id,
                "access_token": access_token,
            }
        )
        if not pub_resp.is_success:
            error_body = pub_resp.text
            logger.error(f"[biel/instagram] Erro ao publicar: {pub_resp.status_code} — {error_body}")
            raise ValueError(f"Instagram publish error {pub_resp.status_code}: {error_body}")
        post_id = pub_resp.json().get("id")
        if not post_id:
            raise ValueError(f"Instagram não retornou post_id: {pub_resp.text}")
        logger.info(f"[biel/instagram] Post publicado! ID: {post_id}")
        return post_id


async def get_account_info(ig_account_id: str, access_token: str) -> dict:
    """Retorna informações básicas da conta Instagram."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_URL}/{ig_account_id}",
            params={
                "fields":       "id,name,username,followers_count,media_count",
                "access_token": access_token,
            }
        )
        resp.raise_for_status()
        return resp.json()
