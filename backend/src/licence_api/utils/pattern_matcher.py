"""Pattern matcher utilities for optimized bulk license processing.

This module provides in-memory pattern matching to avoid N+1 queries during sync.
Patterns are loaded once and matched against all licenses in memory.
"""

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from licence_api.models.orm.admin_account_pattern import AdminAccountPatternORM
    from licence_api.models.orm.service_account_license_type import ServiceAccountLicenseTypeORM
    from licence_api.models.orm.service_account_pattern import ServiceAccountPatternORM


@dataclass
class PatternMatch:
    """Result of a pattern match."""

    matched: bool
    name: str | None = None
    owner_id: UUID | None = None


class PatternMatcher:
    """In-memory pattern matcher for bulk license processing.

    Load patterns once at initialization, then match multiple emails/license types
    without additional database queries.
    """

    def __init__(
        self,
        service_account_patterns: list["ServiceAccountPatternORM"],
        admin_account_patterns: list["AdminAccountPatternORM"],
        service_account_license_types: list["ServiceAccountLicenseTypeORM"],
    ) -> None:
        """Initialize matcher with preloaded patterns.

        Args:
            service_account_patterns: List of service account email patterns
            admin_account_patterns: List of admin account email patterns
            service_account_license_types: List of service account license type rules
        """
        self._svc_patterns = service_account_patterns
        self._admin_patterns = admin_account_patterns
        self._svc_license_types = service_account_license_types

        # Build lookup dict for exact license type matches (case-insensitive)
        self._license_type_lookup: dict[str, ServiceAccountLicenseTypeORM] = {
            lt.license_type.lower(): lt for lt in service_account_license_types
        }

    def match_service_account_email(self, email: str) -> PatternMatch:
        """Match email against service account patterns.

        Args:
            email: Email address to match

        Returns:
            PatternMatch with result
        """
        email_lower = email.lower()

        # First try exact match
        for pattern in self._svc_patterns:
            if pattern.email_pattern.lower() == email_lower:
                return PatternMatch(
                    matched=True,
                    name=pattern.name,
                    owner_id=pattern.owner_id,
                )

        # Then try wildcard patterns
        for pattern in self._svc_patterns:
            pattern_lower = pattern.email_pattern.lower()
            if "*" in pattern_lower or "?" in pattern_lower:
                if fnmatch.fnmatch(email_lower, pattern_lower):
                    return PatternMatch(
                        matched=True,
                        name=pattern.name,
                        owner_id=pattern.owner_id,
                    )

        return PatternMatch(matched=False)

    def match_admin_account_email(self, email: str) -> PatternMatch:
        """Match email against admin account patterns.

        Args:
            email: Email address to match

        Returns:
            PatternMatch with result
        """
        email_lower = email.lower()

        # First try exact match
        for pattern in self._admin_patterns:
            if pattern.email_pattern.lower() == email_lower:
                return PatternMatch(
                    matched=True,
                    name=pattern.name,
                    owner_id=pattern.owner_id,
                )

        # Then try wildcard patterns
        for pattern in self._admin_patterns:
            pattern_lower = pattern.email_pattern.lower()
            if "*" in pattern_lower or "?" in pattern_lower:
                if fnmatch.fnmatch(email_lower, pattern_lower):
                    return PatternMatch(
                        matched=True,
                        name=pattern.name,
                        owner_id=pattern.owner_id,
                    )

        return PatternMatch(matched=False)

    def match_service_account_license_type(self, license_type: str | None) -> PatternMatch:
        """Match license type against service account license type rules.

        Args:
            license_type: License type to match

        Returns:
            PatternMatch with result
        """
        if not license_type:
            return PatternMatch(matched=False)

        entry = self._license_type_lookup.get(license_type.lower())
        if entry:
            return PatternMatch(
                matched=True,
                name=entry.name,
                owner_id=entry.owner_id,
            )

        return PatternMatch(matched=False)
