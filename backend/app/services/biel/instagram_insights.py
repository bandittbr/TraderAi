"""
Biel — Instagram Insights
Coleta métricas de engajamento dos posts publicados via Graph API Insights.
Métricas: likes, comments, shares, saves, reach, impressions, plays, profile visits.
"""

import asyncio
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.models.biel import BielPost, BielPostMetrics, BielToken
from app.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"

# ── Fórmula de engagement score ──────────────────────────────────────────────
# Pesos calibrados para priorizar ações de alto valor:
#   saves > shares > comments > likes ( saves = ação mais "valiosa" no algoritmo )
ENGAGEMENT_WEIGHTS = {
    "likes":     1.0,
    "comments":  3.0,
    "shares":    4.0,
    "saves":     5.0,
}


def _calc_engagement_score(
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    saves: int = 0,
    reach: int = 0,
) -> float:
    """
    Calcula score de engajamento normalizado (0-100).
    Usa soma ponderada / alcance para normalizar entre posts com alcances diferentes.
    """
    raw = (
        likes     * ENGAGEMENT_WEIGHTS["likes"]
        + comments  * ENGAGEMENT_WEIGHTS["comments"]
        + shares    * ENGAGEMENT_WEIGHTS["shares"]
        + saves     * ENGAGEMENT_WEIGHTS["saves"]
    )
    if reach <= 0:
        return float(raw)
    # Normalizar por 1000 views para ter escala comparável
    return round(raw / max(reach, 1) * 1000, 2)


async def fetch_post_insights(
    ig_post_id: str,
    access_token: str,
    media_type: str = "IMAGE",
) -> dict | None:
    """
    Busca métricas de um post específico via Instagram Graph API.

    Para IMAGE: metric=engagement,impressions,reach,saves,likes,comments
    Para VIDEO/REELS: metric=plays,impressions,reach,likes,comments,shares,saves

    Retorna dict com métricas ou None se falhar.
    """
    if media_type == "VIDEO":
        metrics = "plays,impressions,reach,likes,comments,shares,saves"
    else:
        metrics = "engagement,impressions,reach,saves,likes,comments"

    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(
                f"{GRAPH_URL}/{ig_post_id}/insights",
                params={
                    "metric": metrics,
                    "access_token": access_token,
                },
            )

            if not resp.is_success:
                error_data = resp.json().get("error", {})
                code = error_data.get("code", resp.status_code)
                msg = error_data.get("message", resp.text)

                # Error 100: parâmetro inválido (post pode ser Stories/antigo)
                # Error 190: token expirado
                if code == 190:
                    logger.error(f"[biel/insights] Token expirado ou inválido: {msg}")
                    return None
                if code == 10:
                    logger.warning(
                        f"[biel/insights] Post {ig_post_id} não suporta insights "
                        f"(pode ser Stories ou formato antigo): {msg}"
                    )
                    return None
                logger.warning(
                    f"[biel/insights] Erro ao buscar insights de {ig_post_id}: "
                    f"{code} — {msg}"
                )
                return None

            # Parsear resposta: Graph API retorna { "data": [ {"name": "likes", "values": [{"value": N}]}, ... ] }
            data = resp.json().get("data", [])
            metrics_map = {}
            for item in data:
                name = item.get("name", "")
                value = item.get("values", [{}])
                if value:
                    metrics_map[name] = value[0].get("value", 0)

            return {
                "likes":     metrics_map.get("likes", 0),
                "comments":  metrics_map.get("comments", 0),
                "shares":    metrics_map.get("shares", 0),
                "saves":     metrics_map.get("saves", 0),
                "reach":     metrics_map.get("reach", 0),
                "impressions": metrics_map.get("impressions", 0),
                "plays":     metrics_map.get("plays", 0),
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"[biel/insights] HTTP error {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"[biel/insights] Erro inesperado: {e}")
            return None


async def fetch_profile_insights(access_token: str, ig_account_id: str) -> dict | None:
    """
    Busca métricas gerais da conta Instagram.
    Retorna: followers_count, media_count, profile_views (últimos 7d).
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            # Info básica da conta
            resp = await client.get(
                f"{GRAPH_URL}/{ig_account_id}",
                params={
                    "fields": "id,name,username,followers_count,media_count",
                    "access_token": access_token,
                },
            )
            if not resp.is_success:
                logger.error(f"[biel/insights] Erro ao buscar conta: {resp.text}")
                return None

            account_data = resp.json()

            # Insights da conta (últimos 7 dias)
            insights_resp = await client.get(
                f"{GRAPH_URL}/{ig_account_id}/insights",
                params={
                    "metric": "profile_views,reach",
                    "period": "day",
                    "access_token": access_token,
                },
            )

            profile_views_total = 0
            reach_total = 0
            if insights_resp.is_success:
                for item in insights_resp.json().get("data", []):
                    name = item.get("name", "")
                    values = item.get("values", [])
                    total = sum(v.get("value", 0) for v in values)
                    if name == "profile_views":
                        profile_views_total = total
                    elif name == "reach":
                        reach_total = total

            return {
                "followers_count": account_data.get("followers_count", 0),
                "media_count": account_data.get("media_count", 0),
                "profile_views_7d": profile_views_total,
                "reach_7d": reach_total,
            }

        except Exception as e:
            logger.error(f"[biel/insights] Erro ao buscar perfil: {e}")
            return None


async def sync_post_metrics(max_posts: int = 20) -> int:
    """
    Sincroniza métricas de engajamento dos posts publicados recentemente.
    Busca posts sem métricas ou com métricas antigas (>6h) e coleta dados atualizados.

    Retorna número de posts sincronizados.
    """
    logger.info("[biel/insights] Iniciando sincronização de métricas")

    # Buscar token ativo
    from app.services.biel.token_manager import get_active_token
    token = await get_active_token()
    if not token:
        logger.warning("[biel/insights] Nenhum token ativo — ignorando sync")
        return 0

    synced = 0
    cutoff_hours = 6  # re-buscar posts com métricas mais antigas que 6h

    async with AsyncSessionLocal() as session:
        # Buscar posts publicados sem métricas ou com métricas antigas
        # Primeiro: posts publicados que nunca tiveram métricas coletadas
        pub_posts = await session.execute(
            select(BielPost).where(
                BielPost.status == "published",
                BielPost.instagram_id.isnot(None),
                BielPost.instagram_id != "",
            ).order_by(BielPost.published_at.desc()).limit(max_posts)
        )
        posts = pub_posts.scalars().all()

        for post in posts:
            if not post.instagram_id or not post.published_at:
                continue

            # Verificar se já tem métricas recentes
            recent_metric = await session.execute(
                select(BielPostMetrics).where(
                    BielPostMetrics.post_id == post.id,
                    BielPostMetrics.fetched_at >= datetime.now(timezone.utc) - timedelta(hours=cutoff_hours),
                ).order_by(BielPostMetrics.fetched_at.desc()).limit(1)
            )
            existing = recent_metric.scalar_one_or_none()
            if existing:
                continue  # já tem métricas recentes

            # Calcular horas desde a publicação
            hours_after = 0
            if post.published_at:
                delta = datetime.now(timezone.utc) - post.published_at
                hours_after = max(0, int(delta.total_seconds() / 3600))

            # Buscar insights do Instagram
            media_type = "VIDEO" if post.post_type == "reel" else "IMAGE"
            insights = await fetch_post_insights(
                post.instagram_id,
                token.access_token,
                media_type=media_type,
            )

            if insights is None:
                continue

            # Calcular engagement score
            score = _calc_engagement_score(
                likes=insights["likes"],
                comments=insights["comments"],
                shares=insights["shares"],
                saves=insights["saves"],
                reach=insights["reach"],
            )

            # Salvar métricas
            metric = BielPostMetrics(
                post_id=post.id,
                instagram_id=post.instagram_id,
                like_count=insights["likes"],
                comments_count=insights["comments"],
                shares_count=insights["shares"],
                saves_count=insights["saves"],
                reach=insights["reach"],
                impressions=insights["impressions"],
                plays=insights.get("plays", 0),
                engagement_score=score,
                hours_after_post=hours_after,
                post_published_at=post.published_at,
            )
            session.add(metric)
            synced += 1

            # Pequena pausa entre requests para não rate-limit
            await asyncio.sleep(0.5)

        await session.commit()

    if synced > 0:
        logger.info(f"[biel/insights] {synced} posts sincronizados com métricas")
    else:
        logger.debug("[biel/insights] Nenhum post novo para sincronizar")

    return synced
