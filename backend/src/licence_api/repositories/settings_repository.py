"""Settings repository."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.settings import SettingsORM


class SettingsRepository:
    """Repository for application settings."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a setting by key.

        Args:
            key: Setting key

        Returns:
            Setting value or None if not found
        """
        result = await self.session.execute(select(SettingsORM).where(SettingsORM.key == key))
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    async def set(self, key: str, value: dict[str, Any]) -> SettingsORM:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value

        Returns:
            Created or updated SettingsORM
        """
        result = await self.session.execute(select(SettingsORM).where(SettingsORM.key == key))
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        setting = SettingsORM(key=key, value=value)
        self.session.add(setting)
        await self.session.flush()
        await self.session.refresh(setting)
        return setting

    async def delete(self, key: str) -> bool:
        """Delete a setting by key.

        Args:
            key: Setting key

        Returns:
            True if deleted, False if not found
        """
        result = await self.session.execute(select(SettingsORM).where(SettingsORM.key == key))
        setting = result.scalar_one_or_none()

        if setting is None:
            return False

        await self.session.delete(setting)
        await self.session.flush()
        return True

    async def get_all(self) -> dict[str, Any]:
        """Get all settings.

        Returns:
            Dict of all settings
        """
        result = await self.session.execute(select(SettingsORM))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}
