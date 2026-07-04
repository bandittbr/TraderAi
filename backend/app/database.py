"""
TradeAI - Gerenciamento do Banco de Dados SQLite
Utiliza SQLAlchemy assíncrono com aiosqlite para não bloquear o event loop.
Fase 1: apenas inicialização e verificação de conectividade.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from pathlib import Path
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)


def _ensure_db_dir() -> None:
    """Garante que o diretório do banco de dados existe."""
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    # Remove "./" inicial se presente
    if db_path.startswith("./"):
        db_path = db_path[2:]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


# ── Engine assíncrono ──────────────────────────────────────────────────────────
_ensure_db_dir()

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,      # Loga as queries SQL em modo desenvolvimento
    connect_args={"check_same_thread": False},
)

# Fábrica de sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Classe base para todos os modelos SQLAlchemy do TradeAI."""
    pass


async def init_db() -> None:
    """
    Inicializa o banco de dados: cria tabelas e aplica migrações necessárias.
    Chamado na inicialização da aplicação.
    """
    async with engine.begin() as conn:
        # Importar modelos para que o SQLAlchemy os registre no metadata
        import app.models  # noqa: F401 — registra todos os modelos (todas as fases)
        await conn.run_sync(Base.metadata.create_all)

    # ── Migrações incrementais (ALTER TABLE para colunas novas) ──────────────
    await _run_migrations()
    logger.info("Banco de dados inicializado com sucesso.")


async def _run_migrations() -> None:
    """Aplica migrações SQLite de forma idempotente."""
    migrations = [
        # Phase 4+: Futures — adiciona trade_side se não existir
        (
            "paper_trades",
            "trade_side",
            "ALTER TABLE paper_trades ADD COLUMN trade_side TEXT NOT NULL DEFAULT 'LONG'",
        ),
        # Phase 6: analytics — colunas adicionadas gradualmente
        (
            "signal_history",
            "trade_side",
            "ALTER TABLE signal_history ADD COLUMN trade_side TEXT NOT NULL DEFAULT 'LONG'",
        ),
        # Phase 7: Smart Money Context
        ("signal_history", "had_sweep",        "ALTER TABLE signal_history ADD COLUMN had_sweep INTEGER"),
        ("signal_history", "had_fvg",           "ALTER TABLE signal_history ADD COLUMN had_fvg INTEGER"),
        ("signal_history", "had_hvn",           "ALTER TABLE signal_history ADD COLUMN had_hvn INTEGER"),
        ("signal_history", "had_lvn",           "ALTER TABLE signal_history ADD COLUMN had_lvn INTEGER"),
        ("signal_history", "liquidity_score",   "ALTER TABLE signal_history ADD COLUMN liquidity_score REAL"),
        ("signal_history", "liquidity_label",   "ALTER TABLE signal_history ADD COLUMN liquidity_label TEXT"),
        ("signal_history", "sweep_type",        "ALTER TABLE signal_history ADD COLUMN sweep_type TEXT"),
        ("signal_history", "market_structure",  "ALTER TABLE signal_history ADD COLUMN market_structure TEXT"),
        # Phase 8: Signal Engine V6 score columns
        ("signal_history", "raw_score",       "ALTER TABLE signal_history ADD COLUMN raw_score REAL"),
        ("signal_history", "weighted_score",  "ALTER TABLE signal_history ADD COLUMN weighted_score REAL"),
        ("signal_history", "weights_version", "ALTER TABLE signal_history ADD COLUMN weights_version INTEGER DEFAULT 0"),
        # Phase 9: Setup Quality History extras (tabela criada via create_all, colunas adicionais)
        ("setup_quality_history", "outcome",  "ALTER TABLE setup_quality_history ADD COLUMN outcome TEXT"),
        ("setup_quality_history", "pnl_pct",  "ALTER TABLE setup_quality_history ADD COLUMN pnl_pct REAL"),
        # Phase 10: robustness tables created via create_all (no ALTER needed for new tables)
        # Add any future columns here
    ]
    async with engine.begin() as conn:
        for table, column, sql in migrations:
            try:
                # Verifica se a coluna já existe (PRAGMA table_info)
                result = await conn.execute(
                    text(f"PRAGMA table_info({table})")
                )
                cols = [row[1] for row in result.fetchall()]
                if column not in cols:
                    await conn.execute(text(sql))
                    logger.info(f"[migration] {table}.{column} adicionada.")
            except Exception as exc:
                logger.debug(f"[migration] {table}.{column}: {exc}")


async def check_db_connection() -> bool:
    """
    Verifica se o banco de dados está acessível.
    Retorna True se a conexão for bem-sucedida, False caso contrário.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error(f"Falha na conexão com o banco de dados: {exc}")
        return False


async def get_db() -> AsyncSession:
    """
    Dependency Injection do FastAPI: fornece uma sessão de banco de dados
    para cada requisição e garante seu fechamento ao final.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
