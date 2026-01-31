"""Notification rule repository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.notification_rule import NotificationRuleORM
from licence_api.repositories.base import BaseRepository


class NotificationRuleRepository(BaseRepository[NotificationRuleORM]):
    """Repository for notification rule operations."""

    model = NotificationRuleORM

    async def get_enabled_rules(self) -> list[NotificationRuleORM]:
        """Get all enabled notification rules.

        Returns:
            List of enabled notification rules
        """
        result = await self.session.execute(
            select(NotificationRuleORM).where(NotificationRuleORM.enabled == True)
        )
        return list(result.scalars().all())

    async def get_rules_by_event_type(
        self, event_type: str, enabled_only: bool = True
    ) -> list[NotificationRuleORM]:
        """Get notification rules for a specific event type.

        Args:
            event_type: Event type to filter by
            enabled_only: Only return enabled rules (default True)

        Returns:
            List of matching notification rules
        """
        query = select(NotificationRuleORM).where(
            NotificationRuleORM.event_type == event_type
        )
        if enabled_only:
            query = query.where(NotificationRuleORM.enabled == True)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create_rule(
        self,
        event_type: str,
        slack_channel: str,
        template: str | None = None,
        enabled: bool = True,
    ) -> NotificationRuleORM:
        """Create a notification rule.

        Args:
            event_type: Event type to trigger on
            slack_channel: Slack channel to notify
            template: Optional message template
            enabled: Whether the rule is enabled

        Returns:
            Created NotificationRuleORM
        """
        rule = NotificationRuleORM(
            event_type=event_type,
            slack_channel=slack_channel,
            template=template,
            enabled=enabled,
        )
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def update_rule(
        self,
        rule_id: UUID,
        slack_channel: str | None = None,
        template: str | None = None,
        enabled: bool | None = None,
    ) -> NotificationRuleORM | None:
        """Update a notification rule.

        Args:
            rule_id: Rule UUID
            slack_channel: New channel
            template: New template
            enabled: New enabled state

        Returns:
            Updated NotificationRuleORM or None if not found
        """
        rule = await self.get_by_id(rule_id)
        if rule is None:
            return None

        if slack_channel is not None:
            rule.slack_channel = slack_channel
        if template is not None:
            rule.template = template
        if enabled is not None:
            rule.enabled = enabled

        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a notification rule.

        Args:
            rule_id: Rule UUID

        Returns:
            True if deleted, False if not found
        """
        rule = await self.get_by_id(rule_id)
        if rule is None:
            return False

        await self.session.delete(rule)
        await self.session.flush()
        return True
