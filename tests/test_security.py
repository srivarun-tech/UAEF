"""
Tests for UAEF Security Module

Tests for TokenManager, EncryptionService, HashService, and utility functions.
"""

from datetime import timedelta
from unittest.mock import patch

import jwt
import pytest

from uaef.core.security import (
    EncryptionService,
    HashService,
    TokenManager,
    generate_api_key,
    generate_event_id,
)


class MockSecuritySettings:
    """Mock security settings for testing."""

    def __init__(self):
        self.jwt_secret = MockSecretStr("test-secret-key")
        self.jwt_algorithm = "HS256"
        self.jwt_expiration_hours = 24
        self.encryption_key = MockSecretStr("test-encryption-key-32bytes")


class MockLedgerSettings:
    """Mock ledger settings for testing."""

    def __init__(self):
        self.hash_algorithm = "sha256"


class MockSecretStr:
    """Mock SecretStr for testing."""

    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


class MockSettings:
    """Mock settings for testing."""

    def __init__(self):
        self.security = MockSecuritySettings()
        self.ledger = MockLedgerSettings()


@pytest.fixture
def mock_settings():
    """Provide mock settings for security tests."""
    with patch("uaef.core.security.get_settings") as mock:
        mock.return_value = MockSettings()
        yield mock


class TestTokenManager:
    """Tests for TokenManager."""

    def test_create_token(self, mock_settings):
        """Test creating a basic JWT token."""
        manager = TokenManager()
        token = manager.create_token(subject="test-user")

        assert token is not None
        assert isinstance(token, str)

        # Verify token can be decoded
        payload = manager.verify_token(token)
        assert payload["sub"] == "test-user"
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload

    def test_create_token_with_claims(self, mock_settings):
        """Test creating a token with custom claims."""
        manager = TokenManager()
        custom_claims = {"role": "admin", "scope": ["read", "write"]}
        token = manager.create_token(subject="test-user", claims=custom_claims)

        payload = manager.verify_token(token)
        assert payload["sub"] == "test-user"
        assert payload["role"] == "admin"
        assert payload["scope"] == ["read", "write"]

    def test_create_token_with_expiration(self, mock_settings):
        """Test creating a token with custom expiration."""
        manager = TokenManager()
        token = manager.create_token(
            subject="test-user",
            expires_delta=timedelta(hours=1),
        )

        payload = manager.verify_token(token)
        assert payload["sub"] == "test-user"
        # Token should be valid

    def test_create_agent_token(self, mock_settings):
        """Test creating an agent-specific token."""
        manager = TokenManager()
        token = manager.create_agent_token(
            agent_id="agent-123",
            capabilities=["read", "write", "execute"],
        )

        payload = manager.verify_token(token)
        assert payload["sub"] == "agent-123"
        assert payload["type"] == "agent"
        assert payload["capabilities"] == ["read", "write", "execute"]

    def test_verify_invalid_token(self, mock_settings):
        """Test verifying an invalid token raises exception."""
        manager = TokenManager()

        with pytest.raises(jwt.InvalidTokenError):
            manager.verify_token("invalid-token")

    def test_verify_expired_token(self, mock_settings):
        """Test verifying an expired token raises exception."""
        manager = TokenManager()
        token = manager.create_token(
            subject="test-user",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )

        with pytest.raises(jwt.ExpiredSignatureError):
            manager.verify_token(token)


class TestEncryptionService:
    """Tests for EncryptionService."""

    def test_encrypt_decrypt_string(self, mock_settings):
        """Test encrypting and decrypting a string."""
        service = EncryptionService()
        original = "sensitive data"

        encrypted = service.encrypt(original)
        assert encrypted != original
        assert isinstance(encrypted, str)

        decrypted = service.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_dict(self, mock_settings):
        """Test encrypting and decrypting a dictionary."""
        service = EncryptionService()
        original = {
            "username": "test",
            "password": "secret123",
            "nested": {"key": "value"},
        }

        encrypted = service.encrypt_dict(original)
        assert isinstance(encrypted, str)

        decrypted = service.decrypt_dict(encrypted)
        assert decrypted == original

    def test_encryption_is_deterministic(self, mock_settings):
        """Test that same key produces same encryption."""
        service1 = EncryptionService()
        service2 = EncryptionService()

        # Key derivation should be deterministic
        data = "test data"
        # Note: Fernet adds random IV, so ciphertexts will differ
        # but both should decrypt correctly
        encrypted1 = service1.encrypt(data)
        encrypted2 = service2.encrypt(data)

        assert service1.decrypt(encrypted1) == data
        assert service2.decrypt(encrypted2) == data
        # Both services should be able to decrypt each other's data
        assert service1.decrypt(encrypted2) == data
        assert service2.decrypt(encrypted1) == data

    def test_decrypt_invalid_data(self, mock_settings):
        """Test decrypting invalid data raises exception."""
        service = EncryptionService()

        with pytest.raises(Exception):
            service.decrypt("not-valid-encrypted-data")


class TestHashService:
    """Tests for HashService."""

    def test_hash_string(self, mock_settings):
        """Test hashing a string."""
        service = HashService()
        hash_value = service.hash("test data")

        assert hash_value is not None
        assert isinstance(hash_value, str)
        assert len(hash_value) == 64  # SHA256 produces 64 hex chars

    def test_hash_consistency(self, mock_settings):
        """Test that same input produces same hash."""
        service = HashService()
        data = "consistent data"

        hash1 = service.hash(data)
        hash2 = service.hash(data)

        assert hash1 == hash2

    def test_hash_different_inputs(self, mock_settings):
        """Test that different inputs produce different hashes."""
        service = HashService()

        hash1 = service.hash("data1")
        hash2 = service.hash("data2")

        assert hash1 != hash2

    def test_hash_chain(self, mock_settings):
        """Test creating a hash chain."""
        service = HashService()

        previous = service.hash("genesis")
        chained = service.hash_chain(previous, "new data")

        assert chained is not None
        assert chained != previous
        assert len(chained) == 64

    def test_verify_chain(self, mock_settings):
        """Test verifying a hash chain."""
        service = HashService()

        previous = service.hash("genesis")
        data = "new data"
        chained = service.hash_chain(previous, data)

        assert service.verify_chain(previous, data, chained) is True
        assert service.verify_chain(previous, "wrong data", chained) is False
        assert service.verify_chain("wrong hash", data, chained) is False

    def test_hash_event(self, mock_settings):
        """Test hashing an event dictionary."""
        service = HashService()

        event = {
            "type": "workflow_started",
            "workflow_id": "wf-123",
            "timestamp": "2025-01-19T00:00:00Z",
        }

        hash1 = service.hash_event(event)
        hash2 = service.hash_event(event)

        assert hash1 == hash2
        assert len(hash1) == 64

    def test_hash_event_key_order_independent(self, mock_settings):
        """Test that event hash is independent of key order."""
        service = HashService()

        event1 = {"a": 1, "b": 2, "c": 3}
        event2 = {"c": 3, "a": 1, "b": 2}

        # Should produce same hash due to sorted keys
        assert service.hash_event(event1) == service.hash_event(event2)


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_api_key(self):
        """Test generating an API key."""
        key = generate_api_key()

        assert key is not None
        assert key.startswith("uaef_")
        assert len(key) > 10

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]
        assert len(set(keys)) == 100

    def test_generate_event_id(self):
        """Test generating an event ID."""
        event_id = generate_event_id()

        assert event_id is not None
        assert isinstance(event_id, str)
        assert len(event_id) > 10

    def test_generate_event_id_uniqueness(self):
        """Test that generated event IDs are unique."""
        ids = [generate_event_id() for _ in range(100)]
        assert len(set(ids)) == 100
