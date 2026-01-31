"""User notification preference repository."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.user_notification_preference import UserNotificationPreferenceORM
from licence_api.repositories.base import BaseRepository


class UserNotificationPreferenceRepository(BaseRepository[UserNotificationPreferenceORM]):
    """Repository for user notification preference operations."""

    model = UserNotificationPreferenceORM

    async def get_by_user_id(self, user_id: UUID) -> list[UserNotificationPreferenceORM]:
        """Get all notification preferences for a user.

        Args:
            user_id: User UUID

        Returns:
            List of UserNotificationPreferenceORM
        """
        result = await self.session.execute(
            select(UserNotificationPreferenceORM)
            .where(UserNotificationPreferenceORM.user_id == user_id)
            .order_by(UserNotificationPreferenceORM.event_type)
        )
        return list(result.scalars().all())

    async def get_by_user_and_event(
        self,
        user_id: UUID,
        event_type: str,
    ) -> UserNotificationPreferenceORM | None:
        """Get a specific notification preference.

        Args:
            user_id: User UUID
            event_type: Event type string

        Returns:
            UserNotificationPreferenceORM or None
        """
        result = await self.session.execute(
            select(UserNotificationPreferenceORM)
            .where(UserNotificationPreferenceORM.user_id == user_id)
            .where(UserNotificationPreferenceORM.event_type == event_type)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: UUID,
        event_type: str,
        enabled: bool = True,
        slack_dm: bool = False,
        slack_channel: str | None = None,
    ) -> UserNotificationPreferenceORM:
        """Create or update a notification preference.

        Args:
            user_id: User UUID
            event_type: Event type string
            enabled: Whether notifications are enabled
            slack_dm: Whether to send Slack DM
            slack_channel: Custom Slack channel

        Returns:
            Created or updated UserNotificationPreferenceORM
        """
        existing = await self.get_by_user_and_event(user_id, event_type)

        if existing:
            existing.enabled = enabled
            existing.slack_dm = slack_dm
            existing.slack_channel = slack_channel
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            user_id=user_id,
            event_type=event_type,
            enabled=enabled,
            slack_dm=slack_dm,
            slack_channel=slack_channel,
        )

    async def bulk_upsert(
        self,
        user_id: UUID,
        preferences: list[dict],
    ) -> list[UserNotificationPreferenceORM]:
        """Bulk create or update notification preferences.

        Args:
            user_id: User UUID
            preferences: List of preference dicts

        Returns:
            List of UserNotificationPreferenceORM
        """
        results = []
        for pref in preferences:
            result = await self.upsert(
                user_id=user_id,
                event_type=pref["event_type"],
                enabled=pref.get("enabled", True),
                slack_dm=pref.get("slack_dm", False),
                slack_channel=pref.get("slack_channel"),
            )
            results.append(result)
        return results

    async def delete_by_user_id(self, user_id: UUID) -> int:
        """Delete all notification preferences for a user.

        Args:
            user_id: User UUID

        Returns:
            Number of deleted records
        """
        result = await self.session.execute(
            delete(UserNotificationPreferenceORM)
            .where(UserNotificationPreferenceORM.user_id == user_id)
        )
        await self.session.flush()
        return result.rowcount

    async def get_users_for_event(
        self,
        event_type: str,
        enabled_only: bool = True,
    ) -> list[UserNotificationPreferenceORM]:
        """Get all users who have preferences for a specific event type.

        Args:
            event_type: Event type string
            enabled_only: Only return enabled preferences

        Returns:
            List of UserNotificationPreferenceORM with user loaded
        """
        query = select(UserNotificationPreferenceORM).where(
            UserNotificationPreferenceORM.event_type == event_type
        )

        if enabled_only:
            query = query.where(UserNotificationPreferenceORM.enabled == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())
