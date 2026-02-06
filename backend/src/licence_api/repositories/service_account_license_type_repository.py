"""Service Account License Type repository."""

from uuid import UUID

from sqlalchemy import func, select

from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.service_account_license_type import ServiceAccountLicenseTypeORM
from licence_api.repositories.base import BaseRepository


class ServiceAccountLicenseTypeRepository(BaseRepository[ServiceAccountLicenseTypeORM]):
    """Repository for service account license type operations."""

    model = ServiceAccountLicenseTypeORM

    async def get_all(self) -> list[ServiceAccountLicenseTypeORM]:
        """Get all service account license types.

        Returns:
            List of all license types
        """
        result = await self.session.execute(
            select(ServiceAccountLicenseTypeORM).order_by(ServiceAccountLicenseTypeORM.license_type)
        )
        return list(result.scalars().all())

    async def get_by_license_type(self, license_type: str) -> ServiceAccountLicenseTypeORM | None:
        """Get entry by exact license type string.

        Args:
            license_type: The license type string

        Returns:
            Entry or None if not found
        """
        result = await self.session.execute(
            select(ServiceAccountLicenseTypeORM).where(
                ServiceAccountLicenseTypeORM.license_type == license_type
            )
        )
        return result.scalar_one_or_none()

    async def matches_license_type(self, license_type: str) -> ServiceAccountLicenseTypeORM | None:
        """Find an entry that matches the given license type.

        Uses database-level case-insensitive comparison for efficiency.

        Args:
            license_type: The license type to match

        Returns:
            Matching entry or None
        """
        # Use database-level case-insensitive comparison
        result = await self.session.execute(
            select(ServiceAccountLicenseTypeORM)
            .where(
                func.lower(ServiceAccountLicenseTypeORM.license_type) == func.lower(license_type)
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_match_count(self, entry_id: UUID) -> int:
        """Count licenses matching a license type entry.

        Uses database-level aggregation for efficiency.

        Args:
            entry_id: The entry ID

        Returns:
            Number of matching licenses
        """
        entry = await self.get_by_id(entry_id)
        if not entry:
            return 0

        # Use database-level count with case-insensitive comparison
        result = await self.session.execute(
            select(func.count(LicenseORM.id)).where(
                func.lower(LicenseORM.license_type) == func.lower(entry.license_type)
            )
        )
        return result.scalar() or 0

    async def get_all_with_match_counts(self) -> list[tuple[ServiceAccountLicenseTypeORM, int]]:
        """Get all entries with their match counts.

        Returns:
            List of (entry, match_count) tuples
        """
        entries = await self.get_all()

        results = []
        for entry in entries:
            count = await self.get_match_count(entry.id)
            results.append((entry, count))

        return results

    async def find_matching_licenses(self, entry: ServiceAccountLicenseTypeORM) -> list[LicenseORM]:
        """Find all licenses matching a license type entry.

        Uses database-level filtering for efficiency.

        Args:
            entry: The entry to match against

        Returns:
            List of matching licenses
        """
        # Use database-level case-insensitive filtering
        result = await self.session.execute(
            select(LicenseORM).where(
                func.lower(LicenseORM.license_type) == func.lower(entry.license_type)
            )
        )
        return list(result.scalars().all())
