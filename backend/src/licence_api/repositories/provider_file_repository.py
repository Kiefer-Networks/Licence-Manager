"""Provider file repository."""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.provider_file import ProviderFileORM
from licence_api.repositories.base import BaseRepository


class ProviderFileRepository(BaseRepository[ProviderFileORM]):
    """Repository for provider file operations."""

    model = ProviderFileORM

    async def get_by_provider(self, provider_id: UUID) -> list[ProviderFileORM]:
        """Get all files for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            List of ProviderFileORM ordered by created_at descending
        """
        result = await self.session.execute(
            select(ProviderFileORM)
            .where(ProviderFileORM.provider_id == provider_id)
            .order_by(ProviderFileORM.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_provider_and_id(
        self, provider_id: UUID, file_id: UUID
    ) -> ProviderFileORM | None:
        """Get a specific file for a provider.

        Args:
            provider_id: Provider UUID
            file_id: File UUID

        Returns:
            ProviderFileORM or None if not found
        """
        result = await self.session.execute(
            select(ProviderFileORM)
            .where(ProviderFileORM.id == file_id)
            .where(ProviderFileORM.provider_id == provider_id)
        )
        return result.scalar_one_or_none()

    async def create_file(
        self,
        provider_id: UUID,
        filename: str,
        original_name: str,
        file_type: str,
        file_size: int,
        description: str | None = None,
        category: str | None = None,
    ) -> ProviderFileORM:
        """Create a new provider file record.

        Args:
            provider_id: Provider UUID
            filename: Stored filename (UUID-based)
            original_name: Original uploaded filename
            file_type: MIME type
            file_size: File size in bytes
            description: Optional description
            category: Optional category

        Returns:
            Created ProviderFileORM
        """
        file_orm = ProviderFileORM(
            provider_id=provider_id,
            filename=filename,
            original_name=original_name,
            file_type=file_type,
            file_size=file_size,
            description=description,
            category=category,
        )
        self.session.add(file_orm)
        await self.session.flush()
        await self.session.refresh(file_orm)
        return file_orm

    async def delete_file(self, file_orm: ProviderFileORM) -> None:
        """Delete a provider file record.

        Args:
            file_orm: ProviderFileORM to delete
        """
        await self.session.delete(file_orm)
        await self.session.flush()
