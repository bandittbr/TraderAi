"""
TradeAI - Schemas Pydantic: Sistema
DTOs (Data Transfer Objects) para os endpoints de status e saúde do sistema.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class HealthResponse(BaseModel):
    """Resposta do endpoint /health."""
    status: str                   # "healthy" | "degraded" | "unhealthy"
    app_name: str
    version: str
    environment: str
    timestamp: datetime
    database_connected: bool
    uptime_seconds: float


class SystemStatusResponse(BaseModel):
    """Resposta detalhada do endpoint /status."""
    backend_status: str           # "online" | "offline"
    database_status: str          # "connected" | "disconnected"
    app_version: str
    environment: str
    timestamp: datetime
    # Reservado para Fase 2+
    ai_status: Optional[str] = None
    broker_status: Optional[str] = None


class ErrorResponse(BaseModel):
    """Formato padrão de resposta de erro."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
