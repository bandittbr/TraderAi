"""
TradeAI - Ponto de Entrada do Backend
Inicializa o servidor FastAPI com todos os middlewares, rotas e eventos de ciclo de vida.
Fase 2: adiciona background tasks de sincronização de dados de mercado.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.api.router import router
from app.logger import logger


# ── Ciclo de vida da aplicação ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gerencia startup e shutdown do servidor.
    Startup : inicializa banco → inicia background tasks de mercado.
    Shutdown : cancela tasks e libera recursos.
    """
    # --- STARTUP ---
    logger.info("=" * 60)
    logger.info(f"  {settings.app_name} v{settings.app_version} iniciando...")
    logger.info(f"  Ambiente : {settings.app_env}")
    logger.info(f"  Host     : {settings.app_host}:{settings.app_port}")
    logger.info("=" * 60)

    await init_db()

    # Fase 12: migrações de colunas para tabelas existentes
    from app.database_migrations import run_phase12_migrations
    await run_phase12_migrations()

    # Inicia background tasks de dados de mercado (Fase 2)
    # Importação aqui para evitar import circular durante testes unitários
    from app.services.market_data.scheduler import start_background_tasks
    bg_tasks = await start_background_tasks()

    # Fase 13: Scalper Engine — loop independente
    from app.services.scalper.scheduler import start_scalper
    scalper_tasks = await start_scalper()
    bg_tasks.extend(scalper_tasks)

    logger.info("Sistema pronto para receber requisições.")

    yield  # Servidor em execução

    # --- SHUTDOWN ---
    logger.info("Encerrando background tasks...")
    for task in bg_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info(f"{settings.app_name} encerrado.")


# ── Instância FastAPI ──────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "TradeAI — Plataforma de Trading Algorítmico com Inteligência Artificial. "
        "API REST para gerenciamento de dados de mercado, sinais e estratégias."
    ),
    docs_url="/docs" if settings.is_development else None,     # Swagger apenas em dev
    redoc_url="/redoc" if settings.is_development else None,   # ReDoc apenas em dev
    lifespan=lifespan,
)


# ── Middlewares ────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Rotas ──────────────────────────────────────────────────────────────────────

# Prefixo /api/v1 para versionamento — permite adicionar /api/v2 no futuro
app.include_router(router, prefix="/api/v1")


# ── Rota raiz ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Rota raiz — confirma que o servidor está no ar."""
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/system/health",
        }
    )


# ── Execução direta (desenvolvimento) ─────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
