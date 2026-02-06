"""Password hashing and validation utilities."""

from __future__ import annotations

import re
import secrets
from typing import TYPE_CHECKING

import bcrypt

if TYPE_CHECKING:
    from licence_api.models.dto.password_policy import PasswordPolicySettings


class PasswordService:
    """Service for password hashing and validation."""

    # Default password complexity requirements (used when no policy is provided)
    DEFAULT_MIN_LENGTH = 12
    DEFAULT_REQUIRE_UPPERCASE = True
    DEFAULT_REQUIRE_LOWERCASE = True
    DEFAULT_REQUIRE_DIGIT = True
    DEFAULT_REQUIRE_SPECIAL = True
    SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Security settings
    BCRYPT_ROUNDS = 12
    DEFAULT_PASSWORD_HISTORY_COUNT = 5  # Prevent reuse of last N passwords

    # Runtime policy (loaded from database)
    _policy: PasswordPolicySettings | None = None

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
        except (ValueError, UnicodeDecodeError, UnicodeEncodeError):
            # Invalid hash format or encoding issues
            return False

    def set_policy(self, policy: PasswordPolicySettings) -> None:
        """Set the password policy from database settings.

        Args:
            policy: Password policy settings from database
        """
        self._policy = policy

    @property
    def min_length(self) -> int:
        """Get minimum password length from policy or default."""
        if self._policy:
            return self._policy.min_length
        return self.DEFAULT_MIN_LENGTH

    @property
    def require_uppercase(self) -> bool:
        """Get uppercase requirement from policy or default."""
        if self._policy:
            return self._policy.require_uppercase
        return self.DEFAULT_REQUIRE_UPPERCASE

    @property
    def require_lowercase(self) -> bool:
        """Get lowercase requirement from policy or default."""
        if self._policy:
            return self._policy.require_lowercase
        return self.DEFAULT_REQUIRE_LOWERCASE

    @property
    def require_digit(self) -> bool:
        """Get digit requirement from policy or default."""
        if self._policy:
            return self._policy.require_numbers
        return self.DEFAULT_REQUIRE_DIGIT

    @property
    def require_special(self) -> bool:
        """Get special character requirement from policy or default."""
        if self._policy:
            return self._policy.require_special_chars
        return self.DEFAULT_REQUIRE_SPECIAL

    @property
    def password_history_count(self) -> int:
        """Get password history count from policy or default."""
        if self._policy:
            return self._policy.history_count
        return self.DEFAULT_PASSWORD_HISTORY_COUNT

    def validate_password_strength(
        self, password: str, policy: PasswordPolicySettings | None = None
    ) -> tuple[bool, list[str]]:
        """Validate password meets complexity requirements.

        Args:
            password: Password to validate
            policy: Optional policy to use (uses stored policy if not provided)

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Use provided policy, stored policy, or defaults
        if policy:
            min_len = policy.min_length
            req_upper = policy.require_uppercase
            req_lower = policy.require_lowercase
            req_digit = policy.require_numbers
            req_special = policy.require_special_chars
        else:
            min_len = self.min_length
            req_upper = self.require_uppercase
            req_lower = self.require_lowercase
            req_digit = self.require_digit
            req_special = self.require_special

        if len(password) < min_len:
            errors.append(f"Password must be at least {min_len} characters")

        if req_upper and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        if req_lower and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        if req_digit and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        if req_special and not any(c in self.SPECIAL_CHARS for c in password):
            errors.append(
                f"Password must contain at least one special character ({self.SPECIAL_CHARS})"
            )

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
            # Sequential letters
            r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|"
            r"opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
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
        policy: PasswordPolicySettings | None = None,
    ) -> bool:
        """Check if password was previously used.

        Args:
            password: New password to check
            history_hashes: List of previous password hashes
            policy: Optional policy to use

        Returns:
            True if password was used before
        """
        history_count = policy.history_count if policy else self.password_history_count
        for old_hash in history_hashes[-history_count:]:
            if self.verify_password(password, old_hash):
                return True
        return False

    def generate_temporary_password(
        self, length: int | None = None, policy: PasswordPolicySettings | None = None
    ) -> str:
        """Generate a temporary password.

        Args:
            length: Password length (uses policy min_length if not provided)
            policy: Optional policy to determine length and requirements

        Returns:
            Random password meeting complexity requirements
        """
        # Determine password length from policy or default
        if length is None:
            if policy:
                length = max(policy.min_length, 16)  # At least 16 for temp passwords
            else:
                length = max(self.min_length, 16)

        # Determine requirements from policy
        if policy:
            req_upper = policy.require_uppercase
            req_lower = policy.require_lowercase
            req_digit = policy.require_numbers
            req_special = policy.require_special_chars
        else:
            req_upper = self.require_uppercase
            req_lower = self.require_lowercase
            req_digit = self.require_digit
            req_special = self.require_special

        # Build required character set
        password_chars: list[str] = []
        char_pool = ""

        if req_upper:
            password_chars.append(secrets.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
            char_pool += "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        if req_lower:
            password_chars.append(secrets.choice("abcdefghijklmnopqrstuvwxyz"))
            char_pool += "abcdefghijklmnopqrstuvwxyz"

        if req_digit:
            password_chars.append(secrets.choice("0123456789"))
            char_pool += "0123456789"

        if req_special:
            password_chars.append(secrets.choice(self.SPECIAL_CHARS))
            char_pool += self.SPECIAL_CHARS

        # If no requirements, use all character types
        if not char_pool:
            char_pool = (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
                + self.SPECIAL_CHARS
            )

        # Fill rest with random chars from the pool
        while len(password_chars) < length:
            password_chars.append(secrets.choice(char_pool))

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
