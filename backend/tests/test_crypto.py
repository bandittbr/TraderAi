"""
Tests for Fernet encryption (security/crypto.py).
"""
import os
import pytest


class TestEncryptDecrypt:
    """Round-trip encrypt/decrypt with a real Fernet key."""

    @pytest.fixture(autouse=True)
    def _set_key(self, monkeypatch):
        """Set a valid Fernet key for these tests."""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("SECRET_ENCRYPTION_KEY", key)
        # Also update the pydantic-settings singleton directly
        from app.config import settings
        settings.secret_encryption_key = key
        # Reset crypto module cache so it picks up the new key
        import app.security.crypto as crypto_mod
        crypto_mod._fernet = None
        crypto_mod._fernet_checked = False
        yield
        settings.secret_encryption_key = ""

    def test_round_trip(self):
        from app.security.crypto import encrypt_value, decrypt_value
        plaintext = "my-super-secret-api-key-12345"
        encrypted = encrypt_value(plaintext)
        assert encrypted != plaintext, "Encrypted value should differ from plaintext"
        decrypted = decrypt_value(encrypted)
        assert decrypted == plaintext

    def test_different_ciphertext_each_time(self):
        from app.security.crypto import encrypt_value
        plaintext = "same-input"
        a = encrypt_value(plaintext)
        b = encrypt_value(plaintext)
        # Fernet uses random IV — ciphertexts should differ
        # (extremely unlikely to collide)
        assert a != b

    def test_decrypt_plaintext_fallback(self):
        """Legacy plaintext (not Fernet-encrypted) should pass through."""
        from app.security.crypto import decrypt_value
        legacy = "not-encrypted-at-all"
        assert decrypt_value(legacy) == legacy

    def test_encrypted_text_type_decorator(self):
        """EncryptedText TypeDecorator round-trips correctly."""
        from app.security.crypto import EncryptedText
        from sqlalchemy import String
        from sqlalchemy.engine import create_engine

        decorator = EncryptedText()
        # Simulate bind (write)
        bound = decorator.process_bind_param("secret-val", None)
        assert bound != "secret-val"
        # Simulate result (read)
        result = decorator.process_result_value(bound, None)
        assert result == "secret-val"

    def test_none_passthrough(self):
        from app.security.crypto import encrypt_value, decrypt_value
        assert encrypt_value(None) is None
        assert decrypt_value(None) is None


class TestPlaintextFallback:
    """When SECRET_ENCRYPTION_KEY is empty, everything is plaintext."""

    @pytest.fixture(autouse=True)
    def _no_key(self, monkeypatch):
        monkeypatch.setenv("SECRET_ENCRYPTION_KEY", "")
        import app.security.crypto as crypto_mod
        crypto_mod._fernet = None
        crypto_mod._fernet_checked = False
        yield

    def test_encrypt_returns_plaintext(self):
        from app.security.crypto import encrypt_value
        assert encrypt_value("hello") == "hello"

    def test_decrypt_returns_plaintext(self):
        from app.security.crypto import decrypt_value
        assert decrypt_value("hello") == "hello"
