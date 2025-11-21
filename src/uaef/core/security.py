"""
UAEF Security Primitives

Encryption, hashing, and JWT token management for secure
agent communication and data protection.
"""

import hashlib
import hmac
import secrets
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from uaef.core.config import get_settings


class TokenManager:
    """JWT token creation and validation."""

    def __init__(self):
        settings = get_settings()
        self._secret = settings.security.jwt_secret.get_secret_value()
        self._algorithm = settings.security.jwt_algorithm
        self._expiration_hours = settings.security.jwt_expiration_hours

    def create_token(
        self,
        subject: str,
        claims: dict[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT token."""
        now = datetime.now(timezone.utc)

        if expires_delta is None:
            expires_delta = timedelta(hours=self._expiration_hours)

        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + expires_delta,
            "jti": secrets.token_urlsafe(16),
        }

        if claims:
            payload.update(claims)

        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a JWT token."""
        return jwt.decode(token, self._secret, algorithms=[self._algorithm])

    def create_agent_token(self, agent_id: str, capabilities: list[str]) -> str:
        """Create a token for an autonomous agent."""
        return self.create_token(
            subject=agent_id,
            claims={
                "type": "agent",
                "capabilities": capabilities,
            },
        )


class EncryptionService:
    """Data encryption using Fernet symmetric encryption."""

    def __init__(self):
        settings = get_settings()
        key = settings.security.encryption_key.get_secret_value()
        # Derive a proper Fernet key from the configuration key
        self._fernet = Fernet(self._derive_key(key.encode()))

    def _derive_key(self, password: bytes) -> bytes:
        """Derive a Fernet-compatible key from password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"uaef-salt-v1",  # Fixed salt for deterministic key derivation
            iterations=100000,
        )
        return b64encode(kdf.derive(password))

    def encrypt(self, data: str) -> str:
        """Encrypt string data, return base64-encoded ciphertext."""
        encrypted = self._fernet.encrypt(data.encode())
        return b64encode(encrypted).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt base64-encoded ciphertext."""
        ciphertext = b64decode(encrypted_data.encode())
        decrypted = self._fernet.decrypt(ciphertext)
        return decrypted.decode()

    def encrypt_dict(self, data: dict[str, Any]) -> str:
        """Encrypt a dictionary as JSON."""
        import json

        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, encrypted_data: str) -> dict[str, Any]:
        """Decrypt to a dictionary."""
        import json

        return json.loads(self.decrypt(encrypted_data))


class HashService:
    """Cryptographic hashing for ledger integrity."""

    def __init__(self):
        settings = get_settings()
        self._algorithm = settings.ledger.hash_algorithm

    def hash(self, data: str) -> str:
        """Create a hash of string data."""
        hasher = hashlib.new(self._algorithm)
        hasher.update(data.encode())
        return hasher.hexdigest()

    def hash_chain(self, previous_hash: str, data: str) -> str:
        """Create a chained hash linking to previous hash."""
        combined = f"{previous_hash}:{data}"
        return self.hash(combined)

    def verify_chain(self, previous_hash: str, data: str, expected_hash: str) -> bool:
        """Verify a hash chain link."""
        computed = self.hash_chain(previous_hash, data)
        return hmac.compare_digest(computed, expected_hash)

    def hash_event(self, event_data: dict[str, Any]) -> str:
        """Hash an event dictionary in canonical form."""
        import json

        # Canonical JSON representation
        canonical = json.dumps(event_data, sort_keys=True, separators=(",", ":"))
        return self.hash(canonical)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"uaef_{secrets.token_urlsafe(32)}"


def generate_event_id() -> str:
    """Generate a unique event identifier."""
    return secrets.token_urlsafe(16)
