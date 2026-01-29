"""AES-256-GCM encryption service for storing provider credentials."""

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from licence_api.config import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using AES-256-GCM."""

    NONCE_SIZE = 12  # 96 bits for GCM

    def __init__(self, key: str | None = None) -> None:
        """Initialize encryption service with key from settings or provided key."""
        if key is None:
            key = get_settings().encryption_key
        self._key = base64.urlsafe_b64decode(key)
        if len(self._key) != 32:
            raise ValueError("Encryption key must be 32 bytes (256 bits)")
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, data: dict[str, Any]) -> bytes:
        """Encrypt a dictionary to bytes.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted bytes (nonce + ciphertext)
        """
        plaintext = json.dumps(data).encode("utf-8")
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext, None)
        return nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> dict[str, Any]:
        """Decrypt bytes to a dictionary.

        Args:
            encrypted_data: Encrypted bytes (nonce + ciphertext)

        Returns:
            Decrypted dictionary
        """
        nonce = encrypted_data[: self.NONCE_SIZE]
        ciphertext = encrypted_data[self.NONCE_SIZE :]
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))

    def encrypt_string(self, data: str) -> bytes:
        """Encrypt a string to bytes.

        Args:
            data: String to encrypt

        Returns:
            Encrypted bytes
        """
        return self.encrypt({"value": data})

    def decrypt_string(self, encrypted_data: bytes) -> str:
        """Decrypt bytes to a string.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted string
        """
        result = self.decrypt(encrypted_data)
        return result["value"]


# Global instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
