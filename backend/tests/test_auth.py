"""
Tests for API token auth (security/auth.py).
"""
import os
import pytest
from unittest.mock import patch


class TestRequireToken:
    """Test the require_token dependency."""

    def test_dev_mode_no_token_required(self, monkeypatch):
        """Empty API_TOKEN = dev mode, all requests pass."""
        monkeypatch.setenv("API_TOKEN", "")
        from app.config import Settings
        s = Settings()
        assert s.api_token == ""

    def test_production_token_required(self, monkeypatch):
        """Non-empty API_TOKEN means token must be provided."""
        monkeypatch.setenv("API_TOKEN", "test-secret-token")
        from app.config import Settings
        s = Settings()
        assert s.api_token == "test-secret-token"

    @pytest.mark.asyncio
    async def test_valid_token_passes(self, monkeypatch):
        from starlette.testclient import TestClient
        from fastapi import FastAPI
        from app.security.auth import require_token

        monkeypatch.setenv("API_TOKEN", "correct-token")
        # Reset settings singleton
        import app.config as config_mod
        config_mod._settings = None

        app = FastAPI()

        @app.get("/test")
        async def protected(token: str = __import__("fastapi").Depends(require_token)):
            return {"token": token}

        from app.config import settings
        # Force re-read
        settings.api_token = "correct-token"

        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": "Bearer correct-token"})
        assert resp.status_code == 200
        assert resp.json()["token"] == "correct-token"

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, monkeypatch):
        from starlette.testclient import TestClient
        from fastapi import FastAPI
        from app.security.auth import require_token

        monkeypatch.setenv("API_TOKEN", "correct-token")
        import app.config as config_mod
        config_mod._settings = None
        from app.config import settings
        settings.api_token = "correct-token"

        app = FastAPI()

        @app.get("/test")
        async def protected(token: str = __import__("fastapi").Depends(require_token)):
            return {"token": token}

        client = TestClient(app)
        resp = client.get("/test", headers={"Authorization": "Bearer wrong-token"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_token_rejected_when_required(self, monkeypatch):
        from starlette.testclient import TestClient
        from fastapi import FastAPI
        from app.security.auth import require_token

        monkeypatch.setenv("API_TOKEN", "required-token")
        import app.config as config_mod
        config_mod._settings = None
        from app.config import settings
        settings.api_token = "required-token"

        app = FastAPI()

        @app.get("/test")
        async def protected(token: str = __import__("fastapi").Depends(require_token)):
            return {"token": token}

        client = TestClient(app)
        resp = client.get("/test")
        assert resp.status_code == 401
