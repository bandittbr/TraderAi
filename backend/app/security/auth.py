"""
TradeAI Security — API Token authentication.

FastAPI dependency that gates critical endpoints (broker) behind a Bearer token.
Dev mode (API_TOKEN empty) = fully open, so local development is unbroken.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings

_bearer = HTTPBearer(auto_error=False)


async def require_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """
    FastAPI dependency: validates Bearer token against settings.api_token.

    Returns the token string on success.
    Raises 401 if token is required but missing/invalid.

    When settings.api_token is empty (dev mode), all requests pass through.
    """
    required = settings.api_token.strip()
    if not required:
        # Dev mode — no token required
        return ""

    if credentials is None or credentials.credentials != required:
        raise HTTPException(
            status_code=401,
            detail="Token de acesso inválido ou ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials
