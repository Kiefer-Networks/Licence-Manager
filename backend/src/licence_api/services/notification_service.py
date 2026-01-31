"""Notification service for Slack alerts."""

import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.notification_rule import NotificationRuleORM

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending Slack notifications."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session

    async def get_rules(self) -> list[NotificationRuleORM]:
        """Get all notification rules.

        Returns:
            List of notification rules
        """
        result = await self.session.execute(
            select(NotificationRuleORM).where(NotificationRuleORM.enabled == True)
        )
        return list(result.scalars().all())

    async def get_rule(self, rule_id: UUID) -> NotificationRuleORM | None:
        """Get a notification rule by ID.

        Args:
            rule_id: Rule UUID

        Returns:
            NotificationRuleORM or None
        """
        result = await self.session.execute(
            select(NotificationRuleORM).where(NotificationRuleORM.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def create_rule(
        self,
        event_type: str,
        slack_channel: str,
        template: str | None = None,
    ) -> NotificationRuleORM:
        """Create a notification rule.

        Args:
            event_type: Event type to trigger on
            slack_channel: Slack channel to notify
            template: Optional message template

        Returns:
            Created NotificationRuleORM
        """
        rule = NotificationRuleORM(
            event_type=event_type,
            slack_channel=slack_channel,
            template=template,
            enabled=True,
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
            Updated NotificationRuleORM or None
        """
        rule = await self.get_rule(rule_id)
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
        rule = await self.get_rule(rule_id)
        if rule is None:
            return False

        await self.session.delete(rule)
        await self.session.flush()
        return True

    async def notify_employee_offboarded(
        self,
        employee_name: str,
        employee_email: str,
        pending_licenses: list[dict[str, str]],
        slack_token: str,
    ) -> bool:
        """Send notification for offboarded employee.

        Args:
            employee_name: Employee name
            employee_email: Employee email
            pending_licenses: List of pending licenses
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self._get_rules_for_event("employee_offboarded")
        if not rules:
            return False

        license_list = "\n".join(
            f"  • {lic['provider']}: {lic.get('type', 'Unknown')}"
            for lic in pending_licenses
        )

        message = f"""
:warning: *Employee Offboarded Alert*

*Employee:* {employee_name} ({employee_email})

*Pending Licenses ({len(pending_licenses)}):*
{license_list}

Please review and revoke these licenses.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_inactive_license(
        self,
        provider_name: str,
        user_email: str,
        days_inactive: int,
        slack_token: str,
    ) -> bool:
        """Send notification for inactive license.

        Args:
            provider_name: Provider name
            user_email: User email
            days_inactive: Days since last activity
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self._get_rules_for_event("license_inactive")
        if not rules:
            return False

        message = f"""
:zzz: *Inactive License Alert*

*Provider:* {provider_name}
*User:* {user_email}
*Days Inactive:* {days_inactive}

Consider reviewing this license.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_sync_error(
        self,
        provider_name: str,
        error_message: str,
        slack_token: str,
    ) -> bool:
        """Send notification for sync error.

        Args:
            provider_name: Provider name
            error_message: Error details
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self._get_rules_for_event("sync_error")
        if not rules:
            return False

        message = f"""
:x: *Sync Error Alert*

*Provider:* {provider_name}
*Error:* {error_message}

Please check the provider configuration.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_license_expiring(
        self,
        provider_name: str,
        license_type: str | None,
        days_until_expiry: int,
        affected_count: int,
        slack_token: str,
    ) -> bool:
        """Send notification for expiring licenses.

        Args:
            provider_name: Provider name
            license_type: License type (optional)
            days_until_expiry: Days until expiration
            affected_count: Number of affected licenses
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self._get_rules_for_event("license_expiring")
        if not rules:
            return False

        type_str = f" ({license_type})" if license_type else ""
        urgency = ":rotating_light:" if days_until_expiry <= 7 else ":warning:"

        message = f"""
{urgency} *License Expiration Alert*

*Provider:* {provider_name}{type_str}
*Expiring in:* {days_until_expiry} day{"s" if days_until_expiry != 1 else ""}
*Affected Licenses:* {affected_count}

Please review and renew these licenses if needed.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def _get_rules_for_event(self, event_type: str) -> list[NotificationRuleORM]:
        """Get notification rules for an event type.

        Args:
            event_type: Event type

        Returns:
            List of matching rules
        """
        result = await self.session.execute(
            select(NotificationRuleORM)
            .where(NotificationRuleORM.event_type == event_type)
            .where(NotificationRuleORM.enabled == True)
        )
        return list(result.scalars().all())

    async def _send_slack_message(
        self,
        channel: str,
        message: str,
        token: str,
    ) -> bool:
        """Send a Slack message.

        Args:
            channel: Slack channel
            message: Message text
            token: Bot token

        Returns:
            True if sent successfully
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "channel": channel,
                        "text": message,
                        "mrkdwn": True,
                    },
                )
                result = response.json()
                if not result.get("ok"):
                    logger.error(f"Slack API error: {result.get('error')}")
                    return False
                return True
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
