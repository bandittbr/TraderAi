"""
TradeAI - Migrações de Banco de Dados
Adiciona colunas novas a tabelas existentes sem Alembic.
Executado no startup do servidor.
"""

from sqlalchemy import text
from app.database import engine
from app.logger import get_logger

logger = get_logger(__name__)


async def run_phase12_migrations() -> None:
    """
    Fase 12 — Trade Management Engine.
    Adiciona colunas à tabela paper_trades se ainda não existirem.
    """
    new_columns = [
        ("break_even_activated",  "INTEGER DEFAULT 0"),
        ("break_even_timestamp",  "TIMESTAMP"),
        ("trailing_stop_active",  "INTEGER DEFAULT 0"),
        ("trailing_stop_price",   "REAL"),
        ("trailing_stop_peak",    "REAL"),
        ("tp1_hit",               "INTEGER DEFAULT 0"),
        ("tp1_hit_timestamp",     "TIMESTAMP"),
        ("tp1_partial_qty",       "REAL"),
        ("tp1_partial_price",     "REAL"),
        ("remaining_quantity",    "REAL"),
        ("partial_pnl",           "REAL"),
        ("exit_score_at_close",   "REAL"),
        ("fee_cost_pct",          "REAL"),
        ("net_pnl_percent",       "REAL"),
    ]

    from app.config import settings

    async with engine.begin() as conn:
        # Obter colunas existentes
        if settings.is_postgres:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'paper_trades'")
            )
            existing = {row[0] for row in result.fetchall()}
        else:
            result = await conn.execute(text("PRAGMA table_info(paper_trades)"))
            existing = {row[1] for row in result.fetchall()}

        added = 0
        for col_name, col_type in new_columns:
            if col_name not in existing:
                try:
                    await conn.execute(
                        text(f"ALTER TABLE paper_trades ADD COLUMN {col_name} {col_type}")
                    )
                    added += 1
                    logger.debug(f"[migration] paper_trades.{col_name} adicionada")
                except Exception as exc:
                    logger.warning(f"[migration] paper_trades.{col_name}: {exc}")

        if added:
            logger.info(f"[phase12] {added} colunas adicionadas a paper_trades")
        else:
            logger.debug("[phase12] paper_trades já está atualizada")


async def run_signal_history_migration() -> None:
    """
    Adiciona colunas module_scores_json, threshold_distance, fee_cost_pct, net_pnl_pct à signal_history se não existirem.
    """
    from app.config import settings

    new_columns = [
        ("module_scores_json", "TEXT"),
        ("threshold_distance", "REAL"),
        ("fee_cost_pct", "REAL"),
        ("net_pnl_pct", "REAL"),
    ]

    async with engine.begin() as conn:
        if settings.is_postgres:
            result = await conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name = 'signal_history'")
            )
            existing = {row[0] for row in result.fetchall()}
        else:
            result = await conn.execute(text("PRAGMA table_info(signal_history)"))
            existing = {row[1] for row in result.fetchall()}

        added = 0
        for col_name, col_type in new_columns:
            if col_name not in existing:
                try:
                    await conn.execute(
                        text(f"ALTER TABLE signal_history ADD COLUMN {col_name} {col_type}")
                    )
                    added += 1
                    logger.debug(f"[signal-history] {col_name} adicionada")
                except Exception as exc:
                    logger.warning(f"[signal-history] {col_name}: {exc}")

        if added:
            logger.info(f"[signal-history] {added} colunas adicionadas")
        else:
            logger.debug("[signal-history] já está atualizada")


async def run_biel_metrics_migration() -> None:
    """
    Biel Engagement Analytics — cria tabelas biel_post_metrics e biel_topic_performance
    se não existirem.
    """
    from app.config import settings

    create_tables_sql = {
        "biel_post_metrics": """
            CREATE TABLE IF NOT EXISTS biel_post_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL REFERENCES biel_posts(id),
                instagram_id VARCHAR(100) NOT NULL,
                like_count INTEGER DEFAULT 0,
                comments_count INTEGER DEFAULT 0,
                shares_count INTEGER DEFAULT 0,
                saves_count INTEGER DEFAULT 0,
                reach INTEGER DEFAULT 0,
                impressions INTEGER DEFAULT 0,
                plays INTEGER DEFAULT 0,
                profile_visits INTEGER DEFAULT 0,
                follows INTEGER DEFAULT 0,
                engagement_score REAL DEFAULT 0.0,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hours_after_post INTEGER DEFAULT 0,
                post_published_at TIMESTAMP
            )
        """,
        "biel_topic_performance": """
            CREATE TABLE IF NOT EXISTS biel_topic_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic VARCHAR(50) NOT NULL UNIQUE,
                post_type VARCHAR(20) NOT NULL,
                avg_engagement REAL DEFAULT 0.0,
                avg_reach REAL DEFAULT 0.0,
                avg_likes REAL DEFAULT 0.0,
                avg_comments REAL DEFAULT 0.0,
                avg_saves REAL DEFAULT 0.0,
                total_posts INTEGER DEFAULT 0,
                weight REAL DEFAULT 1.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }

    async with engine.begin() as conn:
        for table_name, sql in create_tables_sql.items():
            try:
                await conn.execute(text(sql))
                logger.debug(f"[biel-migration] Tabela {table_name} OK")
            except Exception as exc:
                logger.warning(f"[biel-migration] {table_name}: {exc}")

        # Índices para performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_biemetrics_post_id ON biel_post_metrics(post_id)",
            "CREATE INDEX IF NOT EXISTS idx_biemetrics_ig_id ON biel_post_metrics(instagram_id)",
            "CREATE INDEX IF NOT EXISTS idx_biemetrics_fetched ON biel_post_metrics(fetched_at)",
            "CREATE INDEX IF NOT EXISTS idx_bitoperf_topic ON biel_topic_performance(topic)",
        ]
        for idx_sql in indexes:
            try:
                await conn.execute(text(idx_sql))
            except Exception:
                pass  # índice já existe

    logger.info("[biel-migration] Tabelas de métricas de engajamento criadas/verificadas")
