"""Admin Account Pattern repository."""

import fnmatch
from uuid import UUID

from sqlalchemy import select

from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.admin_account_pattern import AdminAccountPatternORM
from licence_api.repositories.base import BaseRepository


class AdminAccountPatternRepository(BaseRepository[AdminAccountPatternORM]):
    """Repository for admin account pattern operations."""

    model = AdminAccountPatternORM

    async def get_all(self) -> list[AdminAccountPatternORM]:
        """Get all admin account patterns.

        Returns:
            List of all patterns
        """
        result = await self.session.execute(
            select(AdminAccountPatternORM).order_by(AdminAccountPatternORM.email_pattern)
        )
        return list(result.scalars().all())

    async def get_by_email_pattern(self, email_pattern: str) -> AdminAccountPatternORM | None:
        """Get pattern by exact email pattern string.

        Args:
            email_pattern: The pattern string

        Returns:
            Pattern or None if not found
        """
        result = await self.session.execute(
            select(AdminAccountPatternORM).where(
                AdminAccountPatternORM.email_pattern == email_pattern
            )
        )
        return result.scalar_one_or_none()

    async def matches_email(self, email: str) -> AdminAccountPatternORM | None:
        """Find a pattern that matches the given email address.

        Supports:
        - Exact match: "max-admin@example.com"
        - Wildcard patterns: "*-admin@example.com", "admin-*@example.com"

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

    async def get_all_with_match_counts(self) -> list[tuple[AdminAccountPatternORM, int]]:
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

    async def find_matching_licenses(
        self, pattern: AdminAccountPatternORM
    ) -> list[LicenseORM]:
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
