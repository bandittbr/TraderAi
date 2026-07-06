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
