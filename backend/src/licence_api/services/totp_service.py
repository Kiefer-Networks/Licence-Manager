"""TOTP (Time-based One-Time Password) service for two-factor authentication."""

import base64
import hashlib
import hmac
import io
import secrets
import struct
import time
from typing import Any

import qrcode
from qrcode.image.svg import SvgImage

from licence_api.config import get_settings
from licence_api.security.encryption import get_encryption_service


# TOTP Constants (RFC 6238)
TOTP_DIGITS = 6
TOTP_PERIOD = 30  # seconds
TOTP_ALGORITHM = "SHA1"
TOTP_SECRET_LENGTH = 20  # 160 bits, standard for Google Authenticator compatibility

# Backup codes
BACKUP_CODE_COUNT = 10
BACKUP_CODE_LENGTH = 8


class TotpService:
    """Service for TOTP generation and verification.

    Implements RFC 6238 (TOTP) and RFC 4226 (HOTP) for time-based
    one-time password generation and verification.
    """

    def __init__(self) -> None:
        """Initialize TOTP service with encryption service."""
        self.encryption = get_encryption_service()
        self.settings = get_settings()

    def generate_secret(self) -> str:
        """Generate a new TOTP secret key.

        Returns:
            Base32-encoded secret key (RFC 4648)
        """
        # Generate random bytes and encode as base32
        random_bytes = secrets.token_bytes(TOTP_SECRET_LENGTH)
        return base64.b32encode(random_bytes).decode("utf-8").rstrip("=")

    def encrypt_secret(self, secret: str) -> bytes:
        """Encrypt TOTP secret for database storage.

        Args:
            secret: Base32-encoded TOTP secret

        Returns:
            Encrypted bytes
        """
        return self.encryption.encrypt({"totp_secret": secret})

    def decrypt_secret(self, encrypted_data: bytes) -> str:
        """Decrypt TOTP secret from database.

        Args:
            encrypted_data: Encrypted secret bytes

        Returns:
            Base32-encoded TOTP secret
        """
        data = self.encryption.decrypt(encrypted_data)
        return data["totp_secret"]

    def generate_backup_codes(self) -> list[str]:
        """Generate single-use backup codes for account recovery.

        Returns:
            List of backup codes (alphanumeric, easy to type)
        """
        codes = []
        for _ in range(BACKUP_CODE_COUNT):
            # Generate URL-safe base64, then take alphanumeric chars
            raw = secrets.token_urlsafe(BACKUP_CODE_LENGTH)
            # Remove ambiguous characters and format as xxxx-xxxx
            code = "".join(c for c in raw.upper() if c.isalnum())[:BACKUP_CODE_LENGTH]
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        return codes

    def encrypt_backup_codes(self, codes: list[str]) -> bytes:
        """Encrypt backup codes for database storage.

        Stores hashed codes (not plain text) for security.
        Each code can only be used once.

        Args:
            codes: List of plain text backup codes

        Returns:
            Encrypted bytes containing hashed codes
        """
        # Hash each code for storage (we verify against hash, not plain text)
        hashed_codes = [self._hash_backup_code(code) for code in codes]
        return self.encryption.encrypt({"backup_codes": hashed_codes})

    def decrypt_backup_codes(self, encrypted_data: bytes) -> list[str]:
        """Decrypt backup codes from database.

        Args:
            encrypted_data: Encrypted backup codes bytes

        Returns:
            List of hashed backup codes
        """
        data = self.encryption.decrypt(encrypted_data)
        return data.get("backup_codes", [])

    def _hash_backup_code(self, code: str) -> str:
        """Hash a backup code for secure storage.

        Args:
            code: Plain text backup code

        Returns:
            SHA-256 hash of the code
        """
        # Normalize: remove dashes and uppercase
        normalized = code.replace("-", "").upper()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def verify_backup_code(
        self,
        code: str,
        encrypted_codes: bytes,
    ) -> tuple[bool, bytes | None]:
        """Verify a backup code and remove it if valid.

        Args:
            code: Backup code to verify
            encrypted_codes: Encrypted backup codes from database

        Returns:
            Tuple of (is_valid, updated_encrypted_codes or None if no change)
        """
        hashed_codes = self.decrypt_backup_codes(encrypted_codes)
        code_hash = self._hash_backup_code(code)

        if code_hash in hashed_codes:
            # Remove the used code
            hashed_codes.remove(code_hash)
            # Re-encrypt remaining codes
            updated = self.encryption.encrypt({"backup_codes": hashed_codes})
            return True, updated

        return False, None

    def get_provisioning_uri(
        self,
        secret: str,
        email: str,
        issuer: str | None = None,
    ) -> str:
        """Generate TOTP provisioning URI for QR code.

        Format: otpauth://totp/{issuer}:{email}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30

        Args:
            secret: Base32-encoded TOTP secret
            email: User email (account identifier)
            issuer: Application name (default from settings)

        Returns:
            OTPAuth URI string
        """
        if issuer is None:
            issuer = self.settings.app_name or "Licence Manager"

        # URL-encode special characters
        import urllib.parse

        encoded_issuer = urllib.parse.quote(issuer, safe="")
        encoded_email = urllib.parse.quote(email, safe="")

        # Ensure secret has no padding
        secret_clean = secret.rstrip("=")

        return (
            f"otpauth://totp/{encoded_issuer}:{encoded_email}"
            f"?secret={secret_clean}"
            f"&issuer={encoded_issuer}"
            f"&algorithm={TOTP_ALGORITHM}"
            f"&digits={TOTP_DIGITS}"
            f"&period={TOTP_PERIOD}"
        )

    def generate_qr_code_svg(self, provisioning_uri: str) -> str:
        """Generate QR code as SVG string.

        Args:
            provisioning_uri: OTPAuth URI to encode

        Returns:
            SVG string of the QR code
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Generate SVG
        img = qr.make_image(image_factory=SvgImage)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode("utf-8")

    def generate_qr_code_data_uri(self, provisioning_uri: str) -> str:
        """Generate QR code as data URI for embedding in HTML/JSON.

        Args:
            provisioning_uri: OTPAuth URI to encode

        Returns:
            Data URI string (data:image/png;base64,...)
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)

        # Generate PNG
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        png_data = buffer.getvalue()

        # Convert to base64 data URI
        b64 = base64.b64encode(png_data).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def generate_totp(self, secret: str, timestamp: int | None = None) -> str:
        """Generate current TOTP code.

        Implements RFC 6238 TOTP algorithm.

        Args:
            secret: Base32-encoded TOTP secret
            timestamp: Unix timestamp (default: current time)

        Returns:
            6-digit TOTP code
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time counter
        counter = timestamp // TOTP_PERIOD

        # Decode secret (add padding if needed)
        secret_padded = secret + "=" * (8 - len(secret) % 8) if len(secret) % 8 else secret
        key = base64.b32decode(secret_padded.upper())

        # HOTP calculation (RFC 4226)
        counter_bytes = struct.pack(">Q", counter)
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        binary = struct.unpack(">I", hmac_hash[offset : offset + 4])[0] & 0x7FFFFFFF

        # Generate 6-digit code
        otp = binary % (10**TOTP_DIGITS)
        return str(otp).zfill(TOTP_DIGITS)

    def verify_totp(
        self,
        secret: str,
        code: str,
        window: int = 1,
    ) -> bool:
        """Verify a TOTP code with time window tolerance.

        Args:
            secret: Base32-encoded TOTP secret
            code: 6-digit TOTP code to verify
            window: Number of periods to check before/after current time
                    (1 = check -30s, now, +30s)

        Returns:
            True if code is valid within the time window
        """
        if not code or len(code) != TOTP_DIGITS or not code.isdigit():
            return False

        current_time = int(time.time())

        # Check current period and adjacent periods within window
        for offset in range(-window, window + 1):
            timestamp = current_time + (offset * TOTP_PERIOD)
            expected_code = self.generate_totp(secret, timestamp)
            if hmac.compare_digest(code, expected_code):
                return True

        return False


# Global instance
_totp_service: TotpService | None = None


def get_totp_service() -> TotpService:
    """Get or create the TOTP service singleton."""
    global _totp_service
    if _totp_service is None:
        _totp_service = TotpService()
    return _totp_service
