"""
Biel — Instagram Publisher
Publica posts no Instagram via Graph API.
A imagem deve ser acessível via URL pública (servida pelo backend via /biel/images/).
"""

import httpx
from app.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


async def publish_image(
    image_url: str,
    caption: str,
    ig_account_id: str,
    access_token: str,
) -> str:
    """
    Publica uma imagem no Instagram via URL pública.
    Fluxo: criar container → publicar container.
    Retorna o ID do post publicado.
    """
    async with httpx.AsyncClient(timeout=60.0) as client:

        # Passo 1: Criar container de mídia
        resp = await client.post(
            f"{GRAPH_URL}/{ig_account_id}/media",
            data={
                "image_url":    image_url,
                "caption":      caption,
                "access_token": access_token,
            }
        )
        resp.raise_for_status()
        container_id = resp.json().get("id")
        if not container_id:
            raise ValueError(f"Instagram não retornou container_id: {resp.text}")
        logger.info(f"[biel/instagram] Container criado: {container_id}")

        # Passo 2: Publicar o container
        pub_resp = await client.post(
            f"{GRAPH_URL}/{ig_account_id}/media_publish",
            data={
                "creation_id":  container_id,
                "access_token": access_token,
            }
        )
        pub_resp.raise_for_status()
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
