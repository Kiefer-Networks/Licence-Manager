"""Employee external account repository."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from licence_api.models.orm.employee_external_account import EmployeeExternalAccountORM
from licence_api.models.orm.employee import EmployeeORM
from licence_api.repositories.base import BaseRepository


class EmployeeExternalAccountRepository(BaseRepository[EmployeeExternalAccountORM]):
    """Repository for employee external account operations."""

    model = EmployeeExternalAccountORM

    async def get_by_employee(self, employee_id: UUID) -> list[EmployeeExternalAccountORM]:
        """Get all external accounts for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            List of external accounts
        """
        result = await self.session.execute(
            select(EmployeeExternalAccountORM)
            .where(EmployeeExternalAccountORM.employee_id == employee_id)
            .order_by(EmployeeExternalAccountORM.provider_type)
        )
        return list(result.scalars().all())

    async def get_by_provider_and_username(
        self,
        provider_type: str,
        external_username: str,
    ) -> EmployeeExternalAccountORM | None:
        """Get external account by provider and username.

        Args:
            provider_type: Provider type (e.g., "huggingface")
            external_username: Username in the external system

        Returns:
            EmployeeExternalAccountORM or None
        """
        result = await self.session.execute(
            select(EmployeeExternalAccountORM).where(
                and_(
                    EmployeeExternalAccountORM.provider_type == provider_type,
                    EmployeeExternalAccountORM.external_username == external_username,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_employee_by_external_username(
        self,
        provider_type: str,
        external_username: str,
    ) -> EmployeeORM | None:
        """Get employee by their external username.

        Args:
            provider_type: Provider type (e.g., "huggingface")
            external_username: Username in the external system

        Returns:
            EmployeeORM or None
        """
        result = await self.session.execute(
            select(EmployeeORM)
            .join(EmployeeExternalAccountORM)
            .where(
                and_(
                    EmployeeExternalAccountORM.provider_type == provider_type,
                    EmployeeExternalAccountORM.external_username == external_username,
                )
            )
        )
        return result.scalar_one_or_none()

    async def link_account(
        self,
        employee_id: UUID,
        provider_type: str,
        external_username: str,
        external_user_id: str | None = None,
        display_name: str | None = None,
        linked_by_id: UUID | None = None,
    ) -> EmployeeExternalAccountORM:
        """Link an external account to an employee.

        Args:
            employee_id: Employee UUID
            provider_type: Provider type (e.g., "huggingface")
            external_username: Username in the external system
            external_user_id: Optional ID in the external system
            display_name: Optional display name from external system
            linked_by_id: ID of admin who created the link

        Returns:
            Created EmployeeExternalAccountORM
        """
        return await self.create(
            employee_id=employee_id,
            provider_type=provider_type,
            external_username=external_username,
            external_user_id=external_user_id,
            display_name=display_name,
            linked_at=datetime.now(timezone.utc),
            linked_by_id=linked_by_id,
        )

    async def unlink_account(
        self,
        provider_type: str,
        external_username: str,
    ) -> bool:
        """Unlink an external account.

        Args:
            provider_type: Provider type
            external_username: Username in the external system

        Returns:
            True if deleted, False if not found
        """
        account = await self.get_by_provider_and_username(
            provider_type, external_username
        )
        if account is None:
            return False

        await self.session.delete(account)
        await self.session.flush()
        return True

    async def get_all_for_provider(
        self,
        provider_type: str,
    ) -> dict[str, UUID]:
        """Get all username->employee mappings for a provider.

        Args:
            provider_type: Provider type

        Returns:
            Dict mapping external_username to employee_id
        """
        result = await self.session.execute(
            select(
                EmployeeExternalAccountORM.external_username,
                EmployeeExternalAccountORM.employee_id,
            ).where(EmployeeExternalAccountORM.provider_type == provider_type)
        )
        return {row[0]: row[1] for row in result.all()}

    async def find_employee_suggestions(
        self,
        display_name: str,
        provider_type: str,
        limit: int = 5,
    ) -> list[tuple[EmployeeORM, float]]:
        """Find employee suggestions based on name similarity.

        Uses trigram similarity for fuzzy matching.

        Args:
            display_name: Name to match against
            provider_type: Provider type (to exclude already linked employees)
            limit: Maximum number of suggestions

        Returns:
            List of (employee, similarity_score) tuples, ordered by score desc
        """
        if not display_name:
            return []

        # Normalize the search name
        search_name = display_name.strip().lower()

        # Get IDs of employees already linked to this provider
        linked_subquery = (
            select(EmployeeExternalAccountORM.employee_id)
            .where(EmployeeExternalAccountORM.provider_type == provider_type)
            .scalar_subquery()
        )

        # Build query with name similarity
        # We use a combination of ILIKE and similarity scoring
        result = await self.session.execute(
            select(EmployeeORM)
            .where(
                and_(
                    EmployeeORM.status == "active",
                    EmployeeORM.id.notin_(linked_subquery),
                    or_(
                        func.lower(EmployeeORM.full_name).contains(search_name),
                        func.lower(EmployeeORM.full_name).op("~")(
                            self._build_name_pattern(search_name)
                        ),
                    ),
                )
            )
            .limit(limit * 2)  # Get more to score and re-rank
        )
        employees = list(result.scalars().all())

        # Score and rank results
        scored = []
        for emp in employees:
            score = self._calculate_name_similarity(search_name, emp.full_name.lower())
            if score > 0.3:  # Minimum threshold
                scored.append((emp, score))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def _build_name_pattern(self, name: str) -> str:
        """Build a regex pattern for name matching.

        Handles first/last name order variations.

        Args:
            name: Name to build pattern for

        Returns:
            Regex pattern string
        """
        parts = name.split()
        if len(parts) >= 2:
            # Try both "first last" and "last first" patterns
            return f"({parts[0]}.*{parts[-1]}|{parts[-1]}.*{parts[0]})"
        return f".*{name}.*"

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names.

        Uses a combination of:
        - Exact substring match
        - Word overlap
        - Character-level similarity

        Args:
            name1: First name
            name2: Second name

        Returns:
            Similarity score between 0 and 1
        """
        if not name1 or not name2:
            return 0.0

        # Normalize
        name1 = name1.strip().lower()
        name2 = name2.strip().lower()

        # Exact match
        if name1 == name2:
            return 1.0

        # Word-level matching
        words1 = set(name1.split())
        words2 = set(name2.split())

        if not words1 or not words2:
            return 0.0

        # Jaccard similarity on words
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        word_score = intersection / union if union > 0 else 0

        # Partial word matching (for nicknames like "Ben" -> "Benjamin")
        partial_matches = 0
        for w1 in words1:
            for w2 in words2:
                if w1 in w2 or w2 in w1:
                    partial_matches += 1

        partial_score = partial_matches / max(len(words1), len(words2))

        # Combine scores (weighted)
        return 0.7 * word_score + 0.3 * partial_score

    async def bulk_lookup(
        self,
        provider_type: str,
        usernames: list[str],
    ) -> dict[str, EmployeeORM]:
        """Lookup multiple usernames at once.

        Args:
            provider_type: Provider type
            usernames: List of usernames to lookup

        Returns:
            Dict mapping username to EmployeeORM
        """
        if not usernames:
            return {}

        result = await self.session.execute(
            select(
                EmployeeExternalAccountORM.external_username,
                EmployeeORM,
            )
            .join(EmployeeORM)
            .where(
                and_(
                    EmployeeExternalAccountORM.provider_type == provider_type,
                    EmployeeExternalAccountORM.external_username.in_(usernames),
                )
            )
        )
        return {row[0]: row[1] for row in result.all()}
