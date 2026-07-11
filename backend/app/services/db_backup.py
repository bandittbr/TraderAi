"""
TradeAI - Database Backup Service
Backup automático do banco de dados para evitar perda de dados.

Para SQLite: copia o arquivo .db para data/backups/
Para PostgreSQL: usa pg_dump se disponível, senão exporta tabelas críticas como JSON

O backup é feito:
  1. Na inicialização da aplicação
  2. A cada 6 horas automaticamente
  3. Antes de migrações (quando detectadas)
"""

import os
import json
import shutil
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)

BACKUP_DIR = Path("data/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Máximo de backups mantidos (rotaciona)
MAX_BACKUPS = 30


async def run_backup() -> str | None:
    """
    Executa backup do banco de dados.
    Retorna o caminho do backup criado, ou None se falhou.
    """
    try:
        if settings.is_postgres:
            return await _backup_postgres()
        else:
            return await _backup_sqlite()
    except Exception as e:
        logger.error(f"[backup] Erro ao criar backup: {e}")
        return None


async def _backup_sqlite() -> str | None:
    """Backup do arquivo SQLite copiando para data/backups/."""
    db_url = settings.database_url
    # Extrair caminho do arquivo da URL
    # sqlite+aiosqlite:///./data/tradeai.db → ./data/tradeai.db
    db_path = db_url.replace("sqlite+aiosqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    db_file = Path(db_path)
    if not db_file.exists():
        logger.warning(f"[backup] Arquivo SQLite não encontrado: {db_file}")
        return None

    # Criar nome do backup com timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_name = f"tradeai_{timestamp}.db"
    backup_path = BACKUP_DIR / backup_name

    # Copiar arquivo (shutil.copy2 preserva metadados)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, shutil.copy2, str(db_file), str(backup_path))

    # Comprimir gzip para economizar espaço
    import gzip
    gz_path = str(backup_path) + ".gz"

    def _compress():
        with open(backup_path, "rb") as f_in:
            with gzip.open(gz_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        backup_path.unlink()  # Remove o .db não comprimido

    await loop.run_in_executor(None, _compress)

    logger.info(f"[backup] SQLite backup criado: {gz_path}")
    _rotate_backups()
    return gz_path


async def _backup_postgres() -> str | None:
    """
    Backup do PostgreSQL.
    Tenta pg_dump; se não disponível, exporta tabelas críticas como JSON.
    """
    # Tentar pg_dump
    pg_dump_path = shutil.which("pg_dump")
    if pg_dump_path:
        return await _pg_dump_backup(pg_dump_path)
    
    # Fallback: exportar tabelas críticas como JSON
    return await _json_export_backup()


async def _pg_dump_backup(pg_dump_path: str) -> str | None:
    """Backup usando pg_dump."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dump_file = BACKUP_DIR / f"tradeai_{timestamp}.sql.gz"

    # Extrair credenciais da DATABASE_URL
    db_url = settings.database_url.replace("postgresql+asyncpg://", "")
    
    cmd = f'{pg_dump_path} "{db_url}" | gzip > "{dump_file}"'
    
    loop = asyncio.get_event_loop()
    import subprocess
    result = await loop.run_in_executor(
        None,
        lambda: subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    )

    if result.returncode == 0 and dump_file.exists():
        logger.info(f"[backup] PostgreSQL backup criado: {dump_file}")
        _rotate_backups()
        return str(dump_file)
    else:
        logger.error(f"[backup] pg_dump falhou: {result.stderr[:200]}")
        return await _json_export_backup()


async def _json_export_backup() -> str | None:
    """
    Exporta tabelas críticas como JSON (fallback quando pg_dump não disponível).
    Tabelas exportadas: paper_account, paper_trades, scalper_account, scalper_trades,
    worker_account, worker_trades, trade_activity.
    """
    from app.database import AsyncSessionLocal
    from sqlalchemy import text

    CRITICAL_TABLES = [
        "paper_account", "paper_trades",
        "scalper_account", "scalper_trades",
        "worker_account", "worker_trades",
        "trade_activity",
        "trade_lifecycle",
        "signal_history",
    ]

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    export_path = BACKUP_DIR / f"tradeai_{timestamp}.json.gz"

    data = {}
    async with AsyncSessionLocal() as session:
        for table in CRITICAL_TABLES:
            try:
                result = await session.execute(text(f"SELECT * FROM {table}"))
                rows = result.mappings().all()
                data[table] = [dict(row) for row in rows]
                logger.debug(f"[backup] {table}: {len(rows)} linhas exportadas")
            except Exception as e:
                logger.debug(f"[backup] Tabela {table} não existe ou erro: {e}")
                data[table] = []

    # Salvar como JSON comprimido
    import gzip
    loop = asyncio.get_event_loop()

    def _write():
        json_bytes = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
        with gzip.open(export_path, "wb") as f:
            f.write(json_bytes)

    await loop.run_in_executor(None, _write)

    logger.info(f"[backup] JSON export criado: {export_path}")
    _rotate_backups()
    return str(export_path)


def _rotate_backups():
    """Remove backups antigos mantendo apenas MAX_BACKUPS."""
    backups = sorted(BACKUP_DIR.glob("tradeai_*"), key=lambda p: p.stat().st_mtime)
    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        old.unlink(missing_ok=True)
        logger.debug(f"[backup] Backup antigo removido: {old.name}")


async def start_backup_scheduler() -> list:
    """Inicia o scheduler de backup como background task."""
    async def _loop():
        # Backup inicial (com 30s de delay para o DB estar pronto)
        await asyncio.sleep(30)
        await run_backup()

        while True:
            await asyncio.sleep(6 * 3600)  # A cada 6 horas
            await run_backup()

    task = asyncio.create_task(_loop())
    logger.info("[backup] Scheduler de backup iniciado (intervalo: 6h)")
    return [task]
