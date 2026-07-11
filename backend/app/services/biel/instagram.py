"""
Biel — Instagram Publisher
Publica imagens e reels no Instagram via Graph API.
A mídia deve ser acessível via URL pública (servida pelo backend).
"""

import asyncio
import httpx
from app.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


async def _wait_container_ready(
    client: httpx.AsyncClient,
    container_id: str,
    access_token: str,
    media_type: str = "IMAGE",
    max_wait: int = 60,
) -> None:
    """
    Aguarda o container de mídia ficar FINISHED (pronto para publicar).
    Vídeos podem levar mais tempo que imagens.
    """
    for attempt in range(max_wait):
        resp = await client.get(
            f"{GRAPH_URL}/{container_id}",
            params={"fields": "status_code", "access_token": access_token}
        )
        if resp.is_success:
            data = resp.json()
            status = data.get("status_code", "")
            logger.info(
                f"[biel/instagram] Container {media_type} {container_id} "
                f"status: {status} (tentativa {attempt+1})"
            )
            if status == "FINISHED":
                return
            if status == "ERROR":
                # Tentar obter erro detalhado
                err_resp = await client.get(
                    f"{GRAPH_URL}/{container_id}",
                    params={"fields": "status_code,error_message", "access_token": access_token}
                )
                err_detail = ""
                if err_resp.is_success:
                    err_detail = err_resp.json().get("error_message", "")
                raise ValueError(
                    f"Instagram rejeitou o container {media_type}: "
                    f"status ERROR. {err_detail}"
                )
            if status == "EXPIRED":
                raise ValueError(f"Container {media_type} expirou antes de ser publicado.")
        await asyncio.sleep(2)
    raise ValueError(
        f"Container {media_type} não ficou FINISHED após {max_wait * 2}s."
    )


async def publish_media(
    media_url: str,
    caption: str,
    ig_account_id: str,
    access_token: str,
    media_type: str = "IMAGE",
) -> str:
    """
    Publica mídia (imagem ou vídeo/reel) no Instagram via URL pública.
    
    Fluxo: criar container → aguardar FINISHED → publicar container.
    Retorna o ID do post publicado.
    
    Args:
        media_url: URL pública da mídia (imagem ou vídeo)
        caption: Legenda do post
        ig_account_id: Instagram Account ID
        access_token: Access token do Instagram
        media_type: "IMAGE" (post) ou "VIDEO" (reel)
    """
    async with httpx.AsyncClient(timeout=120.0) as client:

        # Passo 1: Criar container de mídia
        media_data = {
            "caption":      caption,
            "access_token": access_token,
        }

        if media_type == "VIDEO":
            # A Graph API descontinuou o valor "VIDEO" pra media_type —
            # pra publicar vídeo no feed agora é obrigatório usar "REELS"
            # (mesmo pra vídeo comum, não só Reels de fato).
            media_data["media_type"] = "REELS"
            media_data["video_url"] = media_url
        else:
            media_data["image_url"] = media_url

        resp = await client.post(
            f"{GRAPH_URL}/{ig_account_id}/media",
            data=media_data,
        )

        if not resp.is_success:
            error_body = resp.text
            logger.error(
                f"[biel/instagram] Erro ao criar container {media_type}: "
                f"{resp.status_code} — {error_body}"
            )
            raise ValueError(
                f"Instagram container error {resp.status_code}: {error_body}"
            )

        container_id = resp.json().get("id")
        if not container_id:
            raise ValueError(
                f"Instagram não retornou container_id: {resp.text}"
            )
        logger.info(f"[biel/instagram] Container {media_type} criado: {container_id}")

        # Passo 2: Aguardar container ficar FINISHED
        wait_time = 120 if media_type == "VIDEO" else 60
        await _wait_container_ready(
            client, container_id, access_token,
            media_type=media_type, max_wait=wait_time,
        )

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
            logger.error(
                f"[biel/instagram] Erro ao publicar {media_type}: "
                f"{pub_resp.status_code} — {error_body}"
            )
            raise ValueError(
                f"Instagram publish error {pub_resp.status_code}: {error_body}"
            )

        post_id = pub_resp.json().get("id")
        if not post_id:
            raise ValueError(
                f"Instagram não retornou post_id: {pub_resp.text}"
            )
        logger.info(f"[biel/instagram] {media_type} publicado! ID: {post_id}")
        return post_id


# Aliases para compatibilidade
async def publish_image(*args, **kwargs) -> str:
    """Publica uma imagem (alias para publish_media com media_type=IMAGE)."""
    return await publish_media(*args, **kwargs, media_type="IMAGE")


async def publish_reel(*args, **kwargs) -> str:
    """Publica um reel/vídeo (alias para publish_media com media_type=VIDEO)."""
    return await publish_media(*args, **kwargs, media_type="VIDEO")


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
