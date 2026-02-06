"""Service Account Pattern repository."""

import fnmatch
from uuid import UUID

from sqlalchemy import select

from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.service_account_pattern import ServiceAccountPatternORM
from licence_api.repositories.base import BaseRepository


class ServiceAccountPatternRepository(BaseRepository[ServiceAccountPatternORM]):
    """Repository for service account pattern operations."""

    model = ServiceAccountPatternORM

    async def get_all(self) -> list[ServiceAccountPatternORM]:
        """Get all service account patterns.

        Returns:
            List of all patterns
        """
        result = await self.session.execute(
            select(ServiceAccountPatternORM).order_by(ServiceAccountPatternORM.email_pattern)
        )
        return list(result.scalars().all())

    async def get_by_email_pattern(self, email_pattern: str) -> ServiceAccountPatternORM | None:
        """Get pattern by exact email pattern string.

        Args:
            email_pattern: The pattern string

        Returns:
            Pattern or None if not found
        """
        result = await self.session.execute(
            select(ServiceAccountPatternORM).where(
                ServiceAccountPatternORM.email_pattern == email_pattern
            )
        )
        return result.scalar_one_or_none()

    async def matches_email(self, email: str) -> ServiceAccountPatternORM | None:
        """Find a pattern that matches the given email address.

        Supports:
        - Exact match: "service@example.com"
        - Wildcard patterns: "svc-*@example.com", "*-bot@example.com"

        Args:
            email: The email address to match

        Returns:
            Matching pattern or None
        """
        patterns = await self.get_all()

        # First try exact match
        email_lower = email.lower()
        for pattern in patterns:
            if pattern.email_pattern.lower() == email_lower:
                return pattern

        # Then try wildcard patterns
        for pattern in patterns:
            pattern_lower = pattern.email_pattern.lower()
            if "*" in pattern_lower or "?" in pattern_lower:
                if fnmatch.fnmatch(email_lower, pattern_lower):
                    return pattern

        return None

    async def get_match_count(self, pattern_id: UUID) -> int:
        """Count licenses matching a pattern.

        Args:
            pattern_id: The pattern ID

        Returns:
            Number of matching licenses
        """
        pattern = await self.get_by_id(pattern_id)
        if not pattern:
            return 0

        # Get all licenses and count matches
        result = await self.session.execute(select(LicenseORM.external_user_id))
        emails = [r[0] for r in result.all()]

        count = 0
        pattern_lower = pattern.email_pattern.lower()
        for email in emails:
            email_lower = email.lower()
            if pattern_lower == email_lower:
                count += 1
            elif "*" in pattern_lower or "?" in pattern_lower:
                if fnmatch.fnmatch(email_lower, pattern_lower):
                    count += 1
        return count

    async def get_all_with_match_counts(self) -> list[tuple[ServiceAccountPatternORM, int]]:
        """Get all patterns with their match counts.

        Returns:
            List of (pattern, match_count) tuples
        """
        patterns = await self.get_all()

        # Get all license emails for matching
        result = await self.session.execute(select(LicenseORM.external_user_id))
        emails = [r[0].lower() for r in result.all()]

        results = []
        for pattern in patterns:
            pattern_lower = pattern.email_pattern.lower()
            count = 0
            for email in emails:
                if pattern_lower == email:
                    count += 1
                elif "*" in pattern_lower or "?" in pattern_lower:
                    if fnmatch.fnmatch(email, pattern_lower):
                        count += 1
            results.append((pattern, count))

        return results

    async def find_matching_licenses(self, pattern: ServiceAccountPatternORM) -> list[LicenseORM]:
        """Find all licenses matching a pattern.

        Args:
            pattern: The pattern to match against

        Returns:
            List of matching licenses
        """
        result = await self.session.execute(select(LicenseORM))
        all_licenses = list(result.scalars().all())

        pattern_lower = pattern.email_pattern.lower()
        matching = []

        for license in all_licenses:
            email_lower = license.external_user_id.lower()
            if pattern_lower == email_lower:
                matching.append(license)
            elif "*" in pattern_lower or "?" in pattern_lower:
                if fnmatch.fnmatch(email_lower, pattern_lower):
                    matching.append(license)

        return matching
