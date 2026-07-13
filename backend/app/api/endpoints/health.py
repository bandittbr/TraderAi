"""
TradeAI - Endpoints: Saúde e Status do Sistema
Expõe informações sobre o estado atual do backend, banco de dados e aplicação.
Esses endpoints são consumidos pelo dashboard do frontend.
"""

import time
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
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


# ── Agent Status ──────────────────────────────────────────────────────────────

class AgentStatusEntry(BaseModel):
    name:           str
    status:         str    # "online" | "offline" | "idle"
    last_execution: str | None = None
    interval_secs:  int | None = None

class AgentsStatusResponse(BaseModel):
    agents: list[AgentStatusEntry]


@router.get("/agents-status", response_model=AgentsStatusResponse)
async def get_agents_status():
    """
    Retorna status de cada agente (online/offline) baseado na última execução.
    Online = executou nos últimos 5 minutos.
    """
    now = datetime.now(timezone.utc)
    threshold = timedelta(minutes=5)
    agents = []

    # ── Worker ──
    try:
        from app.services.worker.trade_engine import worker_engine
        le = worker_engine._last_execution
        is_online = le is not None and (now - le.replace(tzinfo=timezone.utc)) < threshold
        agents.append(AgentStatusEntry(
            name="Worker",
            status="online" if is_online else "idle",
            last_execution=le.isoformat() if le else None,
            interval_secs=60,
        ))
    except Exception:
        agents.append(AgentStatusEntry(name="Worker", status="offline"))

    # ── Scalper ──
    try:
        from app.services.scalper.trade_engine import scalper_engine
        le = scalper_engine._last_execution
        is_online = le is not None and (now - le.replace(tzinfo=timezone.utc)) < threshold
        agents.append(AgentStatusEntry(
            name="Scalper",
            status="online" if is_online else "idle",
            last_execution=le.isoformat() if le else None,
            interval_secs=60,
        ))
    except Exception:
        agents.append(AgentStatusEntry(name="Scalper", status="offline"))

    # ── Paper ──
    try:
        from app.services.paper_trading.trade_engine import trade_engine as paper_engine
        le = paper_engine._last_execution
        is_online = le is not None and (now - le.replace(tzinfo=timezone.utc)) < threshold
        agents.append(AgentStatusEntry(
            name="Paper",
            status="online" if is_online else "idle",
            last_execution=le.isoformat() if le else None,
            interval_secs=60,
        ))
    except Exception:
        agents.append(AgentStatusEntry(name="Paper", status="offline"))

    # ── Groq ──
    try:
        from app.services.groq_agent.trade_engine import groq_engine
        le = groq_engine._last_execution
        is_online = le is not None and (now - le.replace(tzinfo=timezone.utc)) < threshold
        agents.append(AgentStatusEntry(
            name="Groq",
            status="online" if is_online else "idle",
            last_execution=le.isoformat() if le else None,
            interval_secs=60,
        ))
    except Exception:
        agents.append(AgentStatusEntry(name="Groq", status="offline"))

    return AgentsStatusResponse(agents=agents)
