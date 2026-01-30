"""Base repository with common database operations."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository with common CRUD operations."""

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def get(self, id: UUID) -> T | None:
        """Get a record by ID.

        Args:
            id: Record UUID

        Returns:
            Record or None if not found
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, id: UUID) -> T | None:
        """Get a record by ID (alias for get).

        Args:
            id: Record UUID

        Returns:
            Record or None if not found
        """
        return await self.get(id)

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """Get all records with pagination.

        Args:
            offset: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of records
        """
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        """Count total records.

        Returns:
            Total count
        """
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> T:
        """Create a new record.

        Args:
            **kwargs: Field values

        Returns:
            Created record
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update(self, id: UUID, **kwargs: Any) -> T | None:
        """Update a record by ID.

        Args:
            id: Record UUID
            **kwargs: Fields to update

        Returns:
            Updated record or None if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return None

        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, id: UUID) -> bool:
        """Delete a record by ID.

        Args:
            id: Record UUID

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return False

        await self.session.delete(instance)
        await self.session.flush()
        return True
