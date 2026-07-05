"""
Biel — Token Manager
Gerencia tokens de acesso do Instagram — renovação automática.
O token de longa duração expira em 60 dias.
O Biel renova automaticamente quando faltam 7 dias para expirar.
"""

import httpx
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.biel import BielToken
from app.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


async def get_active_token() -> BielToken | None:
    """Retorna o token ativo do banco."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BielToken).where(BielToken.is_active == True).limit(1)
        )
        return result.scalar_one_or_none()


async def exchange_for_long_lived(short_token: str, app_id: str, app_secret: str) -> dict:
    """
    Troca um token curto por um token de longa duração (60 dias).
    Retorna: {"access_token": "...", "expires_in": 5183944}
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_URL}/oauth/access_token",
            params={
                "grant_type":        "fb_exchange_token",
                "client_id":         app_id,
                "client_secret":     app_secret,
                "fb_exchange_token": short_token,
            }
        )
        resp.raise_for_status()
        return resp.json()


async def renew_token(token: BielToken) -> str:
    """
    Renova um token de longa duração existente.
    Facebook permite renovar enquanto o token ainda for válido.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{GRAPH_URL}/oauth/access_token",
            params={
                "grant_type":        "fb_exchange_token",
                "client_id":         token.app_id,
                "client_secret":     token.app_secret,
                "fb_exchange_token": token.access_token,
            }
        )
        resp.raise_for_status()
        data = resp.json()
        new_token = data.get("access_token")
        expires_in = data.get("expires_in", 5183944)  # 60 dias em segundos
        return new_token, expires_in


async def check_and_renew():
    """
    Verifica se o token vai expirar em 7 dias e renova automaticamente.
    Chamado pelo scheduler diariamente.
    """
    token = await get_active_token()
    if not token:
        logger.warning("[biel/token] Nenhum token ativo encontrado")
        return

    if not token.expires_at:
        logger.info("[biel/token] Token sem data de expiração — pode ser permanente")
        return

    now = datetime.now(timezone.utc)
    days_left = (token.expires_at - now).days

    logger.info(f"[biel/token] Token expira em {days_left} dias")

    if days_left <= 7:
        logger.info("[biel/token] Renovando token automaticamente...")
        try:
            new_token_str, expires_in = await renew_token(token)
            new_expiry = now + timedelta(seconds=expires_in)

            async with AsyncSessionLocal() as session:
                db_token = await session.get(BielToken, token.id)
                db_token.access_token    = new_token_str
                db_token.expires_at      = new_expiry
                db_token.last_renewed_at = now
                await session.commit()

            logger.info(f"[biel/token] Token renovado! Nova expiração: {new_expiry.date()}")
        except Exception as e:
            logger.error(f"[biel/token] Falha ao renovar token: {e}")
    else:
        logger.info(f"[biel/token] Token OK — {days_left} dias restantes")


async def get_instagram_account_id(access_token: str) -> str | None:
    """
    Busca o Instagram Business Account ID vinculado ao token.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Buscar páginas do Facebook
            resp = await client.get(
                f"{GRAPH_URL}/me/accounts",
                params={"access_token": access_token, "fields": "id,name,instagram_business_account"}
            )
            resp.raise_for_status()
            data = resp.json()

            for page in data.get("data", []):
                ig = page.get("instagram_business_account")
                if ig:
                    logger.info(f"[biel/token] Instagram Account ID: {ig['id']}")
                    return ig["id"]

        logger.warning("[biel/token] Nenhuma conta Instagram Business encontrada")
        return None
    except Exception as e:
        logger.error(f"[biel/token] Erro ao buscar Instagram Account ID: {e}")
        return None


async def save_initial_token(
    access_token: str,
    app_id: str,
    app_secret: str,
) -> BielToken:
    """
    Salva o token inicial no banco (já convertido para longa duração).
    """
    now = datetime.now(timezone.utc)

    # Trocar por token de longa duração
    try:
        data = await exchange_for_long_lived(access_token, app_id, app_secret)
        long_token = data.get("access_token", access_token)
        expires_in = data.get("expires_in", 5183944)
        expires_at = now + timedelta(seconds=expires_in)
        logger.info(f"[biel/token] Token longa duração obtido. Expira: {expires_at.date()}")
    except Exception as e:
        logger.warning(f"[biel/token] Não foi possível trocar token: {e}. Usando token original.")
        long_token = access_token
        expires_at = now + timedelta(days=60)

    # Buscar Instagram Account ID
    ig_account_id = await get_instagram_account_id(long_token)

    async with AsyncSessionLocal() as session:
        token = BielToken(
            account_id      = ig_account_id or "unknown",
            access_token    = long_token,
            token_type      = "long_lived",
            expires_at      = expires_at,
            app_id          = app_id,
            app_secret      = app_secret,
            last_renewed_at = now,
            is_active       = True,
        )
        session.add(token)
        await session.commit()
        await session.refresh(token)
        logger.info(f"[biel/token] Token salvo no banco. IG Account: {ig_account_id}")
        return token
