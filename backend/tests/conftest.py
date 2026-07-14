"""
TradeAI Test Suite — Shared fixtures.
"""
import os
import pytest

# Force dev mode (no API token required) before any app imports
os.environ.setdefault("API_TOKEN", "")
os.environ.setdefault("SECRET_ENCRYPTION_KEY", "")
os.environ.setdefault("APP_ENV", "development")


@pytest.fixture(autouse=True)
def _reset_fernet_cache():
    """Reset the Fernet singleton between tests so env changes take effect."""
    import app.security.crypto as crypto_mod
    crypto_mod._fernet = None
    crypto_mod._fernet_checked = False
    yield
    crypto_mod._fernet = None
    crypto_mod._fernet_checked = False
