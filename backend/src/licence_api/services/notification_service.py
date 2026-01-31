"""Notification service for Slack alerts."""

import logging
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.notification_rule import NotificationRuleORM
from licence_api.repositories.notification_rule_repository import NotificationRuleRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending Slack notifications."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.rule_repo = NotificationRuleRepository(session)

    async def get_rules(self) -> list[NotificationRuleORM]:
        """Get all enabled notification rules.

        Returns:
            List of notification rules
        """
        return await self.rule_repo.get_enabled_rules()

    async def get_rule(self, rule_id: UUID) -> NotificationRuleORM | None:
        """Get a notification rule by ID.

        Args:
            rule_id: Rule UUID

        Returns:
            NotificationRuleORM or None
        """
        return await self.rule_repo.get_by_id(rule_id)

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
        return await self.rule_repo.create_rule(
            event_type=event_type,
            slack_channel=slack_channel,
            template=template,
            enabled=True,
        )

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
        return await self.rule_repo.update_rule(
            rule_id=rule_id,
            slack_channel=slack_channel,
            template=template,
            enabled=enabled,
        )

    async def delete_rule(self, rule_id: UUID) -> bool:
        """Delete a notification rule.

        Args:
            rule_id: Rule UUID

        Returns:
            True if deleted, False if not found
        """
        return await self.rule_repo.delete_rule(rule_id)

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
        rules = await self.rule_repo.get_rules_by_event_type("employee_offboarded")
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
        rules = await self.rule_repo.get_rules_by_event_type("license_inactive")
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
        rules = await self.rule_repo.get_rules_by_event_type("sync_error")
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
        rules = await self.rule_repo.get_rules_by_event_type("license_expiring")
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
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False

    async def send_test_notification(
        self,
        channel: str,
        token: str,
    ) -> tuple[bool, str]:
        """Send a test notification to verify Slack integration.

        Args:
            channel: Slack channel to send to
            token: Slack bot token

        Returns:
            Tuple of (success, message)
        """
        test_message = (
            ":white_check_mark: *Test Notification*\n\n"
            "This is a test message from the License Management System. "
            "If you received this, your Slack integration is working correctly!"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "channel": channel,
                        "text": test_message,
                        "mrkdwn": True,
                    },
                    timeout=10.0,
                )
                result = response.json()

                if result.get("ok"):
                    return True, f"Test notification sent successfully to {channel}"
                else:
                    error = result.get("error", "Unknown error")
                    return False, f"Failed to send notification: {error}"
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            return False, f"Failed to connect to Slack: {str(e)}"
