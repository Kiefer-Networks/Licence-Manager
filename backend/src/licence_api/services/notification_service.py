"""Notification service for Slack alerts."""

import asyncio
import logging
from typing import ClassVar
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.notification_rule import NotificationRuleORM
from licence_api.repositories.notification_rule_repository import NotificationRuleRepository
from licence_api.repositories.settings_repository import SettingsRepository

logger = logging.getLogger(__name__)

# Slack API constants
SLACK_API_BASE = "https://slack.com/api"
SLACK_TIMEOUT = 10.0
SLACK_MAX_RETRIES = 3
SLACK_RETRY_DELAY = 1.0  # Base delay in seconds

# User-Agent per RFC 7231
USER_AGENT = "LicenseManagementSystem/1.0 (https://github.com/Kiefer-Networks/Licence-Manager)"


class NotificationService:
    """Service for sending Slack notifications."""

    # Shared HTTP client for connection reuse (class-level)
    _http_client: ClassVar[httpx.AsyncClient | None] = None

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.rule_repo = NotificationRuleRepository(session)
        self.settings_repo = SettingsRepository(session)

    @classmethod
    def _get_http_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client with connection pooling.

        Returns:
            Shared httpx.AsyncClient instance
        """
        if cls._http_client is None or cls._http_client.is_closed:
            cls._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(SLACK_TIMEOUT),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
                headers={"User-Agent": USER_AGENT},
            )
        return cls._http_client

    @classmethod
    async def close_client(cls) -> None:
        """Close the shared HTTP client. Call on application shutdown."""
        if cls._http_client and not cls._http_client.is_closed:
            await cls._http_client.aclose()
            cls._http_client = None

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
            f"  • {lic['provider']}: {lic.get('type', 'Unknown')}" for lic in pending_licenses
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

    async def notify_license_expired(
        self,
        provider_name: str,
        license_type: str | None,
        user_email: str,
        expired_count: int,
        slack_token: str,
    ) -> bool:
        """Send notification for expired licenses.

        Args:
            provider_name: Provider name
            license_type: License type (optional)
            user_email: User email (or "Multiple users")
            expired_count: Number of expired licenses
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("license_expired")
        if not rules:
            return False

        type_str = f" ({license_type})" if license_type else ""
        user_str = user_email if expired_count == 1 else f"{expired_count} licenses"

        message = f"""
:no_entry: *License Expired Alert*

*Provider:* {provider_name}{type_str}
*Affected:* {user_str}

These licenses have expired and require immediate attention.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_license_cancelled(
        self,
        provider_name: str,
        license_type: str | None,
        user_email: str,
        cancelled_by: str,
        cancellation_reason: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for cancelled licenses.

        Args:
            provider_name: Provider name
            license_type: License type (optional)
            user_email: User email
            cancelled_by: User who cancelled
            cancellation_reason: Reason for cancellation (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("license_cancelled")
        if not rules:
            return False

        type_str = f" ({license_type})" if license_type else ""
        reason_str = f"\n*Reason:* {cancellation_reason}" if cancellation_reason else ""

        message = f"""
:x: *License Cancelled*

*Provider:* {provider_name}{type_str}
*User:* {user_email}
*Cancelled by:* {cancelled_by}{reason_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_package_expired(
        self,
        provider_name: str,
        package_name: str,
        seat_count: int,
        slack_token: str,
    ) -> bool:
        """Send notification for expired package.

        Args:
            provider_name: Provider name
            package_name: Package/license type name
            seat_count: Number of seats in package
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("package_expired")
        if not rules:
            return False

        message = f"""
:no_entry: *Package Expired Alert*

*Provider:* {provider_name}
*Package:* {package_name}
*Seats:* {seat_count}

This package has expired and requires renewal or removal.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_package_cancelled(
        self,
        provider_name: str,
        package_name: str,
        seat_count: int,
        cancelled_by: str,
        cancellation_reason: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for cancelled package.

        Args:
            provider_name: Provider name
            package_name: Package/license type name
            seat_count: Number of seats in package
            cancelled_by: User who cancelled
            cancellation_reason: Reason for cancellation (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("package_cancelled")
        if not rules:
            return False

        reason_str = f"\n*Reason:* {cancellation_reason}" if cancellation_reason else ""

        message = f"""
:x: *Package Cancelled*

*Provider:* {provider_name}
*Package:* {package_name}
*Seats:* {seat_count}
*Cancelled by:* {cancelled_by}{reason_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_org_license_expired(
        self,
        provider_name: str,
        org_license_name: str,
        slack_token: str,
    ) -> bool:
        """Send notification for expired organization license.

        Args:
            provider_name: Provider name
            org_license_name: Organization license name
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("org_license_expired")
        if not rules:
            return False

        message = f"""
:no_entry: *Organization License Expired Alert*

*Provider:* {provider_name}
*License:* {org_license_name}

This organization license has expired and requires renewal.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_org_license_cancelled(
        self,
        provider_name: str,
        org_license_name: str,
        cancelled_by: str,
        cancellation_reason: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for cancelled organization license.

        Args:
            provider_name: Provider name
            org_license_name: Organization license name
            cancelled_by: User who cancelled
            cancellation_reason: Reason for cancellation (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("org_license_cancelled")
        if not rules:
            return False

        reason_str = f"\n*Reason:* {cancellation_reason}" if cancellation_reason else ""

        message = f"""
:x: *Organization License Cancelled*

*Provider:* {provider_name}
*License:* {org_license_name}
*Cancelled by:* {cancelled_by}{reason_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_license_renewed(
        self,
        provider_name: str,
        license_type: str | None,
        user_email: str,
        renewed_by: str,
        new_expiration_date: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for renewed license.

        Args:
            provider_name: Provider name
            license_type: License type (optional)
            user_email: User email
            renewed_by: User who renewed
            new_expiration_date: New expiration date (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("license_renewed")
        if not rules:
            return False

        type_str = f" ({license_type})" if license_type else ""
        expiry_str = f"\n*New Expiration:* {new_expiration_date}" if new_expiration_date else ""

        message = f"""
:white_check_mark: *License Renewed*

*Provider:* {provider_name}{type_str}
*User:* {user_email}
*Renewed by:* {renewed_by}{expiry_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_license_needs_reorder(
        self,
        provider_name: str,
        license_type: str | None,
        user_email: str,
        flagged_by: str,
        slack_token: str,
    ) -> bool:
        """Send notification when license is flagged for reorder.

        Args:
            provider_name: Provider name
            license_type: License type (optional)
            user_email: User email
            flagged_by: User who flagged for reorder
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("license_needs_reorder")
        if not rules:
            return False

        type_str = f" ({license_type})" if license_type else ""

        message = f"""
:shopping_cart: *License Needs Reorder*

*Provider:* {provider_name}{type_str}
*User:* {user_email}
*Flagged by:* {flagged_by}

This license has been flagged for reordering.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_package_renewed(
        self,
        provider_name: str,
        package_name: str,
        seat_count: int,
        renewed_by: str,
        new_contract_end: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for renewed package.

        Args:
            provider_name: Provider name
            package_name: Package/license type name
            seat_count: Number of seats in package
            renewed_by: User who renewed
            new_contract_end: New contract end date (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("package_renewed")
        if not rules:
            return False

        expiry_str = f"\n*New Contract End:* {new_contract_end}" if new_contract_end else ""

        message = f"""
:white_check_mark: *Package Renewed*

*Provider:* {provider_name}
*Package:* {package_name}
*Seats:* {seat_count}
*Renewed by:* {renewed_by}{expiry_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_package_needs_reorder(
        self,
        provider_name: str,
        package_name: str,
        seat_count: int,
        flagged_by: str,
        slack_token: str,
    ) -> bool:
        """Send notification when package is flagged for reorder.

        Args:
            provider_name: Provider name
            package_name: Package/license type name
            seat_count: Number of seats in package
            flagged_by: User who flagged for reorder
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("package_needs_reorder")
        if not rules:
            return False

        message = f"""
:shopping_cart: *Package Needs Reorder*

*Provider:* {provider_name}
*Package:* {package_name}
*Seats:* {seat_count}
*Flagged by:* {flagged_by}

This package has been flagged for reordering.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_org_license_renewed(
        self,
        provider_name: str,
        org_license_name: str,
        renewed_by: str,
        new_expiration_date: str | None,
        slack_token: str,
    ) -> bool:
        """Send notification for renewed organization license.

        Args:
            provider_name: Provider name
            org_license_name: Organization license name
            renewed_by: User who renewed
            new_expiration_date: New expiration date (optional)
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("org_license_renewed")
        if not rules:
            return False

        expiry_str = f"\n*New Expiration:* {new_expiration_date}" if new_expiration_date else ""

        message = f"""
:white_check_mark: *Organization License Renewed*

*Provider:* {provider_name}
*License:* {org_license_name}
*Renewed by:* {renewed_by}{expiry_str}
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def notify_org_license_needs_reorder(
        self,
        provider_name: str,
        org_license_name: str,
        flagged_by: str,
        slack_token: str,
    ) -> bool:
        """Send notification when organization license is flagged for reorder.

        Args:
            provider_name: Provider name
            org_license_name: Organization license name
            flagged_by: User who flagged for reorder
            slack_token: Slack bot token

        Returns:
            True if notification sent successfully
        """
        rules = await self.rule_repo.get_rules_by_event_type("org_license_needs_reorder")
        if not rules:
            return False

        message = f"""
:shopping_cart: *Organization License Needs Reorder*

*Provider:* {provider_name}
*License:* {org_license_name}
*Flagged by:* {flagged_by}

This organization license has been flagged for reordering.
"""

        for rule in rules:
            await self._send_slack_message(
                channel=rule.slack_channel,
                message=message,
                token=slack_token,
            )

        return True

    async def send_test_notification_with_config(
        self,
        channel: str,
    ) -> tuple[bool, str]:
        """Send a test notification using the stored Slack configuration.

        Fetches the Slack bot token from settings and sends a test message.
        This encapsulates the multi-service orchestration that would otherwise
        need to happen in the router layer.

        Args:
            channel: Slack channel to send to

        Returns:
            Tuple of (success, message)
        """
        slack_config = await self.settings_repo.get("slack")

        if not slack_config or not slack_config.get("bot_token"):
            return False, (
                "Slack bot token not configured. "
                "Please configure Slack settings first."
            )

        bot_token = slack_config["bot_token"]
        return await self.send_test_notification(channel=channel, token=bot_token)

    async def _send_slack_message(
        self,
        channel: str,
        message: str,
        token: str,
    ) -> bool:
        """Send a Slack message with retry and rate limit handling.

        Implements exponential backoff for transient failures and
        respects Slack's Retry-After header for rate limiting.

        Args:
            channel: Slack channel (name or ID)
            message: Message text (mrkdwn format)
            token: Slack bot token

        Returns:
            True if sent successfully
        """
        client = self._get_http_client()
        headers = {"Authorization": f"Bearer {token}"}

        for attempt in range(SLACK_MAX_RETRIES):
            try:
                response = await client.post(
                    f"{SLACK_API_BASE}/chat.postMessage",
                    headers=headers,
                    json={
                        "channel": channel,
                        "text": message,
                        "mrkdwn": True,
                    },
                )

                # Handle rate limiting (HTTP 429)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", SLACK_RETRY_DELAY))
                    logger.warning(f"Slack rate limited, retrying after {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                result = response.json()

                if result.get("ok"):
                    return True

                error = result.get("error", "unknown_error")

                # Non-retryable errors
                non_retryable = (
                    "channel_not_found",
                    "invalid_auth",
                    "token_revoked",
                    "not_in_channel",
                )
                if error in non_retryable:
                    logger.error(f"Slack API error (non-retryable): {error}")
                    return False

                # Retryable error - use exponential backoff
                if attempt < SLACK_MAX_RETRIES - 1:
                    delay = SLACK_RETRY_DELAY * (2**attempt)
                    logger.warning(f"Slack API error: {error}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Slack API error after {SLACK_MAX_RETRIES} attempts: {error}")
                    return False

            except httpx.TimeoutException:
                if attempt < SLACK_MAX_RETRIES - 1:
                    delay = SLACK_RETRY_DELAY * (2**attempt)
                    logger.warning(f"Slack request timeout, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error("Slack request timeout after max retries")
                    return False

            except httpx.HTTPError as e:
                logger.error(f"HTTP error sending Slack message: {e}")
                return False

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

        client = self._get_http_client()

        try:
            response = await client.post(
                f"{SLACK_API_BASE}/chat.postMessage",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "channel": channel,
                    "text": test_message,
                    "mrkdwn": True,
                },
            )

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                return False, f"Rate limited by Slack. Retry after {retry_after} seconds."

            result = response.json()

            if result.get("ok"):
                return True, f"Test notification sent successfully to {channel}"

            error = result.get("error", "Unknown error")
            error_messages = {
                "channel_not_found": f"Channel '{channel}' not found",
                "not_in_channel": f"Bot is not a member of '{channel}'",
                "invalid_auth": "Invalid bot token",
                "token_revoked": "Bot token has been revoked",
                "missing_scope": "Bot is missing required 'chat:write' scope",
            }
            return False, error_messages.get(error, f"Slack API error: {error}")

        except httpx.TimeoutException:
            return False, "Request to Slack timed out"
        except httpx.HTTPError as e:
            return False, f"Failed to connect to Slack: {str(e)}"
