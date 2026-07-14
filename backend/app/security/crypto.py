"""
TradeAI Security — Fernet encryption at rest.

Transparent encrypt/decrypt for sensitive DB fields.
Migration-friendly: if SECRET_ENCRYPTION_KEY is not set, plaintext passthrough with warning.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import TypeDecorator, String

from app.config import settings

logger = logging.getLogger(__name__)

_fernet = None
_fernet_checked = False


def _get_fernet():
    """Lazy-init Fernet from settings. Returns None if key not set."""
    global _fernet, _fernet_checked
    if _fernet_checked:
        return _fernet
    _fernet_checked = True

    key = settings.secret_encryption_key.strip()
    if not key:
        logger.warning(
            "[crypto] SECRET_ENCRYPTION_KEY não definido — "
            "dados sensíveis serão armazenados em plaintext. "
            "Defina a variável de ambiente para ativar a encriptação."
        )
        return None

    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        logger.info("[crypto] Fernet encryption ATIVO")
    except Exception as e:
        logger.error(f"[crypto] Falha ao inicializar Fernet: {e}. Dados ficarão em plaintext.")
        _fernet = None

    return _fernet


def encrypt_value(plaintext: str | None) -> str | None:
    """Encrypt a string value. Returns plaintext if no key configured."""
    if plaintext is None:
        return None
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a string value. Tries Fernet first, falls back to plaintext (migration)."""
    if ciphertext is None:
        return None
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except Exception:
        # Not Fernet-encrypted — likely legacy plaintext. Return as-is.
        return ciphertext


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy TypeDecorator that transparently encrypts/decrypts Text columns.

    Usage:
        gemini_api_key = Column(EncryptedText, nullable=False)

    Migration-friendly: existing plaintext rows decrypt correctly (fallback).
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt on write to DB."""
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt on read from DB."""
        if value is None:
            return None
        return decrypt_value(value)
