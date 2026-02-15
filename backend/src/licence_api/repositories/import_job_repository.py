"""Import job repository."""

from uuid import UUID

from sqlalchemy import select

from licence_api.models.orm.import_job import ImportJobORM
from licence_api.repositories.base import BaseRepository


class ImportJobRepository(BaseRepository[ImportJobORM]):
    """Repository for import job operations."""

    model = ImportJobORM

    async def get_by_provider_and_id(
        self,
        provider_id: UUID,
        job_id: UUID,
    ) -> ImportJobORM | None:
        """Get import job by provider and job ID.

        Args:
            provider_id: Provider UUID
            job_id: Import job UUID

        Returns:
            ImportJobORM or None if not found
        """
        result = await self.session.execute(
            select(ImportJobORM).where(
                ImportJobORM.id == job_id,
                ImportJobORM.provider_id == provider_id,
            )
        )
        return result.scalar_one_or_none()
