"""AES-256-GCM encryption service with key versioning for secure key rotation."""

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from licence_api.config import get_settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using AES-256-GCM.

    Supports key versioning for seamless key rotation:
    - New data is always encrypted with the current (latest) key
    - Old data can be decrypted with any known key version
    - Version byte prefix identifies which key was used

    Data format:
    - Version 0 (legacy): nonce (12 bytes) + ciphertext (no version prefix)
    - Version 1+: version (1 byte) + nonce (12 bytes) + ciphertext
    """

    NONCE_SIZE = 12  # 96 bits for GCM
    VERSION_SIZE = 1  # 1 byte for version (0-255)
    CURRENT_VERSION = 1  # Current encryption version

    def __init__(
        self,
        current_key: str | None = None,
        legacy_keys: list[str] | None = None,
    ) -> None:
        """Initialize encryption service with current key and optional legacy keys.

        Args:
            current_key: Current encryption key (base64-encoded, 32 bytes decoded)
            legacy_keys: List of legacy keys for decryption (oldest to newest)
        """
        settings = get_settings()

        # Load current key
        if current_key is None:
            current_key = settings.encryption_key

        self._current_key = self._decode_key(current_key)
        self._current_aesgcm = AESGCM(self._current_key)

        # Load legacy keys for decryption
        self._key_chain: list[bytes] = []

        if legacy_keys is not None:
            for key in legacy_keys:
                self._key_chain.append(self._decode_key(key))
        elif settings.encryption_key_legacy:
            for key in settings.encryption_key_legacy.split(","):
                key = key.strip()
                if key:
                    self._key_chain.append(self._decode_key(key))

        # Add current key as the latest in the chain
        self._key_chain.append(self._current_key)

    def _decode_key(self, key: str) -> bytes:
        """Decode and validate a base64-encoded encryption key."""
        decoded = base64.urlsafe_b64decode(key)
        if len(decoded) != 32:
            raise ValueError("Encryption key must be 32 bytes (256 bits)")
        return decoded

    def encrypt(self, data: dict[str, Any]) -> bytes:
        """Encrypt a dictionary to bytes using the current key.

        Args:
            data: Dictionary to encrypt

        Returns:
            Encrypted bytes (version + nonce + ciphertext)
        """
        plaintext = json.dumps(data).encode("utf-8")
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._current_aesgcm.encrypt(nonce, plaintext, None)

        # Prepend version byte (current version uses latest key index)
        version = len(self._key_chain) - 1  # Index of current key
        return bytes([version]) + nonce + ciphertext

    def decrypt(self, encrypted_data: bytes) -> dict[str, Any]:
        """Decrypt bytes to a dictionary, trying appropriate key(s).

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted dictionary

        Raises:
            ValueError: If decryption fails with all available keys
        """
        if len(encrypted_data) < self.NONCE_SIZE + 1:
            raise ValueError("Invalid encrypted data: too short")

        # Check if data has version prefix (version 1+) or is legacy (version 0)
        first_byte = encrypted_data[0]

        # Heuristic: if first byte is a valid version index, treat as versioned
        # Otherwise, treat as legacy unversioned data
        if first_byte < len(self._key_chain):
            # Versioned data: first byte is key index
            version = first_byte
            nonce = encrypted_data[self.VERSION_SIZE : self.VERSION_SIZE + self.NONCE_SIZE]
            ciphertext = encrypted_data[self.VERSION_SIZE + self.NONCE_SIZE :]

            # Try the specified key version first
            key = self._key_chain[version]
            try:
                aesgcm = AESGCM(key)
                plaintext = aesgcm.decrypt(nonce, ciphertext, None)
                return json.loads(plaintext.decode("utf-8"))
            except Exception:
                pass  # Fall through to try all keys

        # Legacy format or version key failed: try all keys
        # For legacy data: nonce is at position 0
        for offset in [self.VERSION_SIZE, 0]:  # Try versioned offset first, then legacy
            if len(encrypted_data) < offset + self.NONCE_SIZE + 1:
                continue

            nonce = encrypted_data[offset : offset + self.NONCE_SIZE]
            ciphertext = encrypted_data[offset + self.NONCE_SIZE :]

            # Try all keys, newest to oldest (more likely to succeed)
            for key in reversed(self._key_chain):
                try:
                    aesgcm = AESGCM(key)
                    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
                    return json.loads(plaintext.decode("utf-8"))
                except Exception:
                    continue

        raise ValueError("Decryption failed: no valid key found")

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

    def re_encrypt(self, encrypted_data: bytes) -> bytes:
        """Re-encrypt data with the current key.

        Useful for key rotation: decrypt with old key, re-encrypt with new key.

        Args:
            encrypted_data: Data encrypted with any known key

        Returns:
            Data re-encrypted with current key
        """
        data = self.decrypt(encrypted_data)
        return self.encrypt(data)


# Global instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get or create the encryption service singleton."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def reset_encryption_service() -> None:
    """Reset the encryption service singleton (for testing or key rotation)."""
    global _encryption_service
    _encryption_service = None
