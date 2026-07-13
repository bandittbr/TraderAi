"""
Biel — Engagement Analyzer
Analisa performance de engajamento por tópico e atualiza pesos adaptativos.
O cycle de feedback: coleta métricas → analisa por tópico → ajusta pesos → _pick_reel_topic usa pesos.
"""

import math
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func as sqlfunc, desc

from app.database import AsyncSessionLocal
from app.models.biel import BielPost, BielPostMetrics, BielTopicPerformance
from app.logger import get_logger

logger = get_logger(__name__)

# ── Configuração do adaptador ────────────────────────────────────────────────
DECAY_HALF_LIFE_DAYS = 14    # Posts mais recentes pesam mais (meia-vida de 14 dias)
MIN_POSTS_FOR_ADAPT = 2     # Mínimo de posts com métricas para começar a adaptar
WEIGHT_SPEED_LIMIT = 0.3    # Máxima mudança por ciclo (evita oscilação brusca)
WEIGHT_MIN = 0.3            # Peso mínimo (nunca zera um tópico)
WEIGHT_MAX = 3.0            # Peso máximo (nunca sobrepõe totalmente)
WEIGHT_NEUTRAL = 1.0        # Peso neutro (baseline)


def _decay_weight(hours_since_post: int) -> float:
    """
    Peso temporal exponencial: posts recentes pesam mais.
    Ex: 0h = 1.0, 24h = 0.95, 168h (7d) = 0.71, 336h (14d) = 0.5
    """
    half_life_hours = DECAY_HALF_LIFE_DAYS * 24
    return math.exp(-0.693 * hours_since_post / half_life_hours)


def _topic_label(topic: str) -> str:
    """Label legível para logging."""
    labels = {
        "meme": "Meme", "noticias": "Noticias", "insight": "Insight",
        "profits": "Profits", "erros": "Erros", "aprendizados": "Aprendizados",
        "market": "Mercado", "trade": "Trade", "news": "Noticia",
    }
    return labels.get(topic, topic)


async def update_topic_performance() -> dict:
    """
    Recalcula a performance média de cada tópico baseado nas métricas coletadas.
    Usa média ponderada temporal (posts recentes pesam mais).

    Retorna dict com a performance de cada tópico para logging.
    """
    logger.info("[biel/analyzer] Atualizando performance por tópico")
    results = {}

    async with AsyncSessionLocal() as session:
        # Buscar todos os tópicos que têm posts publicados com métricas
        topics_with_metrics = await session.execute(
            select(
                BielPost.reel_topic,
                BielPostMetrics.like_count,
                BielPostMetrics.comments_count,
                BielPostMetrics.shares_count,
                BielPostMetrics.saves_count,
                BielPostMetrics.reach,
                BielPostMetrics.impressions,
                BielPostMetrics.engagement_score,
                BielPostMetrics.hours_after_post,
                BielPostMetrics.post_published_at,
            )
            .join(BielPostMetrics, BielPost.id == BielPostMetrics.post_id)
            .where(
                BielPost.post_type == "reel",
                BielPost.reel_topic.isnot(None),
                BielPost.status == "published",
            )
            .order_by(BielPostMetrics.post_published_at.desc())
        )
        rows = topics_with_metrics.all()

        if not rows:
            logger.info("[biel/analyzer] Nenhuma métrica encontrada para analisar")
            return results

        # Agrupar por tópico e calcular médias ponderadas
        topic_data: dict[str, list] = {}
        for row in rows:
            topic = row[0]
            if not topic:
                continue
            if topic not in topic_data:
                topic_data[topic] = []
            topic_data[topic].append({
                "likes": row[1] or 0,
                "comments": row[2] or 0,
                "shares": row[3] or 0,
                "saves": row[4] or 0,
                "reach": row[5] or 0,
                "impressions": row[6] or 0,
                "engagement_score": row[7] or 0,
                "hours_ago": row[8] or 0,
            })

        now = datetime.now(timezone.utc)

        for topic, posts in topic_data.items():
            if len(posts) < 1:
                continue

            # Calcular médias ponderadas temporalmente
            total_weight = 0
            weighted_likes = 0
            weighted_comments = 0
            weighted_shares = 0
            weighted_saves = 0
            weighted_reach = 0
            weighted_score = 0

            for p in posts:
                w = _decay_weight(p["hours_ago"])
                total_weight += w
                weighted_likes += p["likes"] * w
                weighted_comments += p["comments"] * w
                weighted_shares += p["shares"] * w
                weighted_saves += p["saves"] * w
                weighted_reach += p["reach"] * w
                weighted_score += p["engagement_score"] * w

            if total_weight <= 0:
                continue

            avg_likes = weighted_likes / total_weight
            avg_comments = weighted_comments / total_weight
            avg_shares = weighted_shares / total_weight
            avg_saves = weighted_saves / total_weight
            avg_reach = weighted_reach / total_weight
            avg_score = weighted_score / total_weight

            # ── Calcular peso adaptativo ────────────────────────────────
            # Comparar com a média global de todos os tópicos
            global_avg_score = sum(
                d["engagement_score"] for posts_list in topic_data.values()
                for d in posts_list
            ) / max(len(rows), 1)

            if global_avg_score > 0 and len(posts) >= MIN_POSTS_FOR_ADAPT:
                # Razão entre performance do tópico vs média global
                ratio = avg_score / global_avg_score
                # Aplicar sigmoid para suavizar: ratio 1.0 → weight 1.0, ratio 2.0 → ~1.6
                raw_weight = WEIGHT_NEUTRAL * (2 / (1 + math.exp(-1.5 * (ratio - 1))))
                # Clamp e speed limit
                raw_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, raw_weight))
            else:
                raw_weight = WEIGHT_NEUTRAL

            # Buscar peso atual (se existe) para aplicar speed limit
            existing = await session.execute(
                select(BielTopicPerformance).where(
                    BielTopicPerformance.topic == topic,
                    BielTopicPerformance.post_type == "reel",
                )
            )
            existing_perf = existing.scalar_one_or_none()

            if existing_perf:
                current_weight = existing_perf.weight
                # Speed limit: não mudar mais que WEIGHT_SPEED_LIMIT por ciclo
                delta = raw_weight - current_weight
                if abs(delta) > WEIGHT_SPEED_LIMIT:
                    delta = WEIGHT_SPEED_LIMIT if delta > 0 else -WEIGHT_SPEED_LIMIT
                new_weight = max(WEIGHT_MIN, min(WEIGHT_MAX, current_weight + delta))

                existing_perf.avg_engagement = avg_score
                existing_perf.avg_reach = avg_reach
                existing_perf.avg_likes = avg_likes
                existing_perf.avg_comments = avg_comments
                existing_perf.avg_saves = avg_saves
                existing_perf.total_posts = len(posts)
                existing_perf.weight = new_weight
                existing_perf.last_updated = now
            else:
                new_weight = raw_weight
                perf = BielTopicPerformance(
                    topic=topic,
                    post_type="reel",
                    avg_engagement=avg_score,
                    avg_reach=avg_reach,
                    avg_likes=avg_likes,
                    avg_comments=avg_comments,
                    avg_saves=avg_saves,
                    total_posts=len(posts),
                    weight=new_weight,
                    last_updated=now,
                )
                session.add(perf)

            results[topic] = {
                "avg_score": round(avg_score, 2),
                "avg_reach": round(avg_reach, 0),
                "avg_likes": round(avg_likes, 1),
                "total_posts": len(posts),
                "weight": round(new_weight, 3),
            }

        await session.commit()

    # Log resumido
    for topic, data in sorted(results.items(), key=lambda x: x[1]["weight"], reverse=True):
        logger.info(
            f"[biel/analyzer] {_topic_label(topic)}: "
            f"score={data['avg_score']}, reach={data['avg_reach']:.0f}, "
            f"posts={data['total_posts']}, weight={data['weight']}"
        )

    return results


async def get_topic_weights() -> dict[str, float]:
    """
    Retorna pesos adaptativos dos tópicos para uso no _pick_reel_topic().
    Se não houver dados suficientes, retorna pesos neutros (1.0).
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(BielTopicPerformance).where(
                BielTopicPerformance.post_type == "reel",
            )
        )
        perfs = result.scalars().all()

        if not perfs:
            return {}

        return {p.topic: p.weight for p in perfs}


async def get_engagement_summary() -> dict:
    """
    Retorna resumo de engajamento para o dashboard.
    Inclui: métricas totais, performance por tópico, top posts.
    """
    async with AsyncSessionLocal() as session:
        # Total de métricas coletadas
        metrics_count = await session.execute(
            select(sqlfunc.count(BielPostMetrics.id))
        )
        total_metrics = metrics_count.scalar() or 0

        # Métricas agregadas (soma de todos os posts)
        agg = await session.execute(
            select(
                sqlfunc.sum(BielPostMetrics.like_count),
                sqlfunc.sum(BielPostMetrics.comments_count),
                sqlfunc.sum(BielPostMetrics.shares_count),
                sqlfunc.sum(BielPostMetrics.saves_count),
                sqlfunc.sum(BielPostMetrics.reach),
                sqlfunc.sum(BielPostMetrics.impressions),
                sqlfunc.avg(BielPostMetrics.engagement_score),
            )
        )
        row = agg.one()
        total_likes = row[0] or 0
        total_comments = row[1] or 0
        total_shares = row[2] or 0
        total_saves = row[3] or 0
        total_reach = row[4] or 0
        total_impressions = row[5] or 0
        avg_engagement = row[6] or 0

        # Performance por tópico
        topic_q = await session.execute(
            select(BielTopicPerformance)
            .order_by(desc(BielTopicPerformance.weight))
        )
        topics = [
            {
                "topic": p.topic,
                "weight": round(p.weight, 3),
                "avg_engagement": round(p.avg_engagement, 2),
                "avg_reach": round(p.avg_reach, 0),
                "avg_likes": round(p.avg_likes, 1),
                "avg_saves": round(p.avg_saves, 1),
                "total_posts": p.total_posts,
            }
            for p in topic_q.scalars().all()
        ]

        # Top 5 posts por engagement score
        top_q = await session.execute(
            select(BielPostMetrics, BielPost.reel_topic, BielPost.topic)
            .join(BielPost, BielPost.id == BielPostMetrics.post_id)
            .order_by(desc(BielPostMetrics.engagement_score))
            .limit(5)
        )
        top_posts = [
            {
                "instagram_id": m.instagram_id,
                "topic": reel_t or img_t or "unknown",
                "likes": m.like_count,
                "comments": m.comments_count,
                "shares": m.shares_count,
                "saves": m.saves_count,
                "reach": m.reach,
                "engagement_score": m.engagement_score,
                "published_at": m.post_published_at.isoformat() if m.post_published_at else None,
            }
            for m, reel_t, img_t in top_q.all()
        ]

        return {
            "total_posts_with_metrics": total_metrics,
            "totals": {
                "likes": total_likes,
                "comments": total_comments,
                "shares": total_shares,
                "saves": total_saves,
                "reach": total_reach,
                "impressions": total_impressions,
            },
            "avg_engagement_score": round(avg_engagement, 2),
            "topic_performance": topics,
            "top_posts": top_posts,
        }
