"""Password hashing and validation utilities."""

import re
import secrets
from datetime import datetime, timezone

import bcrypt


class PasswordService:
    """Service for password hashing and validation."""

    # Password complexity requirements
    MIN_LENGTH = 12
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Security settings
    BCRYPT_ROUNDS = 12
    PASSWORD_HISTORY_COUNT = 5  # Prevent reuse of last N passwords

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        salt = bcrypt.gensalt(rounds=self.BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against a hash.

        Args:
            password: Plain text password
            hashed: Hashed password

        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def validate_password_strength(self, password: str) -> tuple[bool, list[str]]:
        """Validate password meets complexity requirements.

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        if len(password) < self.MIN_LENGTH:
            errors.append(f"Password must be at least {self.MIN_LENGTH} characters")

        if self.REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if self.REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if self.REQUIRE_DIGIT and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if self.REQUIRE_SPECIAL and not any(c in self.SPECIAL_CHARS for c in password):
            errors.append(f"Password must contain at least one special character ({self.SPECIAL_CHARS})")

        # Check for common patterns
        if self._contains_common_patterns(password):
            errors.append("Password contains common patterns")

        return len(errors) == 0, errors

    def _contains_common_patterns(self, password: str) -> bool:
        """Check if password contains common weak patterns.

        Args:
            password: Password to check

        Returns:
            True if contains weak patterns
        """
        weak_patterns = [
            r"12345",
            r"qwerty",
            r"password",
            r"admin",
            r"letmein",
            r"welcome",
            r"(.)\1{3,}",  # Same char repeated 4+ times
            r"(012|123|234|345|456|567|678|789)",  # Sequential numbers
            r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",  # Sequential letters
        ]

        password_lower = password.lower()
        for pattern in weak_patterns:
            if re.search(pattern, password_lower):
                return True
        return False

    def check_password_history(
        self,
        password: str,
        history_hashes: list[str],
    ) -> bool:
        """Check if password was previously used.

        Args:
            password: New password to check
            history_hashes: List of previous password hashes

        Returns:
            True if password was used before
        """
        for old_hash in history_hashes[-self.PASSWORD_HISTORY_COUNT :]:
            if self.verify_password(password, old_hash):
                return True
        return False

    def generate_temporary_password(self, length: int = 16) -> str:
        """Generate a temporary password.

        Args:
            length: Password length

        Returns:
            Random password meeting complexity requirements
        """
        # Ensure we have at least one of each required type
        password_chars = [
            secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            secrets.choice("abcdefghijklmnopqrstuvwxyz"),
            secrets.choice("0123456789"),
            secrets.choice(self.SPECIAL_CHARS),
        ]

        # Fill rest with random chars from all categories
        all_chars = (
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            + self.SPECIAL_CHARS
        )

        while len(password_chars) < length:
            password_chars.append(secrets.choice(all_chars))

        # Shuffle the password
        secrets.SystemRandom().shuffle(password_chars)

        return "".join(password_chars)


# Singleton instance
_password_service: PasswordService | None = None


def get_password_service() -> PasswordService:
    """Get the password service singleton.

    Returns:
        PasswordService instance
    """
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service
