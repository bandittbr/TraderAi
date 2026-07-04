"""
TradeAI - Endpoints: Saúde e Status do Sistema
Expõe informações sobre o estado atual do backend, banco de dados e aplicação.
Esses endpoints são consumidos pelo dashboard do frontend.
"""

import time
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.schemas.system import HealthResponse, SystemStatusResponse
from app.database import check_db_connection
from app.config import settings
from app.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Registra o horário de início do processo para cálculo de uptime
_START_TIME: float = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificação de saúde do sistema",
    description="Retorna o estado geral da aplicação e da conexão com o banco de dados.",
)
async def health_check() -> HealthResponse:
    """
    Endpoint de health check.
    Utilizado por ferramentas de monitoramento e pelo frontend para
    determinar se o backend está operacional.
    """
    db_ok = await check_db_connection()
    uptime = time.time() - _START_TIME

    overall_status = "healthy" if db_ok else "degraded"
    logger.info(f"Health check — status={overall_status} uptime={uptime:.1f}s db={db_ok}")

    return HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
        database_connected=db_ok,
        uptime_seconds=round(uptime, 2),
    )


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="Status detalhado do sistema",
    description="Retorna o status de cada componente da plataforma.",
)
async def system_status() -> SystemStatusResponse:
    """
    Status expandido consumido pelo painel de controle do dashboard.
    Na Fase 2+ incluirá status da IA e da corretora conectada.
    """
    db_connected = await check_db_connection()

    return SystemStatusResponse(
        backend_status="online",
        database_status="connected" if db_connected else "disconnected",
        app_version=settings.app_version,
        environment=settings.app_env,
        timestamp=datetime.now(timezone.utc),
        ai_status=None,      # Fase 2
        broker_status=None,  # Fase 2
    )
