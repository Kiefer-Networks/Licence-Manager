"""Settings service for managing application settings."""

from typing import Any
from uuid import UUID

from fastapi import Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.repositories.user_repository import UserRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.notification_service import NotificationService


def validate_setting_recursive(
    data: Any, max_depth: int = 5, current_depth: int = 0, max_items: int = 50
) -> None:
    """Recursively validate dict/list structures to prevent DoS attacks.

    Args:
        data: Data to validate
        max_depth: Maximum nesting depth
        current_depth: Current recursion depth
        max_items: Maximum items per dict/list
    """
    if current_depth > max_depth:
        raise ValueError(f"Setting nesting too deep (max {max_depth} levels)")

    if isinstance(data, dict):
        if len(data) > max_items:
            raise ValueError(f"Too many setting fields (max {max_items})")
        for key, value in data.items():
            if not isinstance(key, str):
                raise ValueError("Setting keys must be strings")
            if len(key) > 100:
                raise ValueError("Setting key too long (max 100 chars)")
            validate_setting_recursive(value, max_depth, current_depth + 1, max_items)
    elif isinstance(data, list):
        if len(data) > max_items:
            raise ValueError(f"Too many items in setting list (max {max_items})")
        for item in data:
            validate_setting_recursive(item, max_depth, current_depth + 1, max_items)
    elif isinstance(data, str):
        if len(data) > 10000:
            raise ValueError("Setting value too long (max 10000 chars)")
    elif isinstance(data, (int, float, bool, type(None))):
        pass
    else:
        raise ValueError(f"Invalid setting value type: {type(data).__name__}")


class NotificationRuleResponse(BaseModel):
    """Notification rule response DTO."""

    id: UUID
    event_type: str
    slack_channel: str
    enabled: bool
    template: str | None = None


class SetupStatus:
    """Setup status data class."""

    def __init__(
        self,
        is_complete: bool,
        has_hibob: bool = False,
        has_providers: bool = False,
        has_admin: bool = False,
    ) -> None:
        self.is_complete = is_complete
        self.has_hibob = has_hibob
        self.has_providers = has_providers
        self.has_admin = has_admin


class SettingsService:
    """Service for managing application settings."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.settings_repo = SettingsRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.user_repo = UserRepository(session)
        self.audit_service = AuditService(session)
        self.notification_service = NotificationService(session)

    async def get_setup_status(self, detailed: bool = False) -> SetupStatus:
        """Get setup status.

        Args:
            detailed: Whether to include detailed status info

        Returns:
            SetupStatus with completion flags
        """
        has_any_provider = await self.provider_repo.exists_any()
        hibob = await self.provider_repo.get_by_name("hibob")
        admin_count = await self.user_repo.count_admins()

        has_hibob = hibob is not None
        has_providers = has_any_provider
        has_admin = admin_count > 0
        is_complete = has_providers and has_hibob and has_admin

        return SetupStatus(
            is_complete=is_complete,
            has_hibob=has_hibob,
            has_providers=has_providers,
            has_admin=has_admin,
        )

    async def get_all(self) -> dict[str, Any]:
        """Get all settings."""
        return await self.settings_repo.get_all()

    async def get(self, key: str) -> dict[str, Any] | None:
        """Get a specific setting by key."""
        return await self.settings_repo.get(key)

    async def set(
        self,
        key: str,
        value: dict[str, Any],
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            The set value
        """
        await self.settings_repo.set(key, value)

        if user:
            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.SETTING,
                resource_id=key,
                user=user,
                request=request,
                details={"key": key},
            )

        await self.session.commit()
        return value

    async def delete(
        self,
        key: str,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Delete a setting.

        Args:
            key: Setting key
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            True if deleted, False if not found
        """
        deleted = await self.settings_repo.delete(key)

        if deleted and user:
            await self.audit_service.log(
                action=AuditAction.SETTING_DELETE,
                resource_type=ResourceType.SETTING,
                resource_id=key,
                user=user,
                request=request,
                details={"key": key},
            )
            await self.session.commit()

        return deleted

    async def set_company_domains(
        self,
        domains: list[str],
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> list[str]:
        """Set company domains.

        Args:
            domains: List of domain strings
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            The normalized domains list
        """
        old_setting = await self.settings_repo.get("company_domains")
        old_domains = old_setting.get("domains", []) if old_setting else []

        # Normalize domains
        normalized_domains = [d.strip().lower() for d in domains if d.strip()]
        await self.settings_repo.set("company_domains", {"domains": normalized_domains})

        if user:
            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.SETTING,
                resource_id="company_domains",
                user=user,
                request=request,
                details={"old_domains": old_domains, "new_domains": normalized_domains},
            )

        await self.session.commit()
        return normalized_domains

    async def set_thresholds(
        self,
        thresholds: dict[str, Any],
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Set threshold settings.

        Args:
            thresholds: Threshold settings dict
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            The set thresholds
        """
        old_settings = await self.settings_repo.get("thresholds")
        await self.settings_repo.set("thresholds", thresholds)

        if user:
            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.SETTING,
                resource_id="thresholds",
                user=user,
                request=request,
                details={"old": old_settings, "new": thresholds},
            )

        await self.session.commit()
        return thresholds

    # Notification rules methods

    async def get_notification_rules(self) -> list[NotificationRuleResponse]:
        """Get all notification rules.

        Returns:
            List of NotificationRuleResponse DTOs
        """
        rules = await self.notification_service.get_rules()
        return [
            NotificationRuleResponse(
                id=r.id,
                event_type=r.event_type,
                slack_channel=r.slack_channel,
                enabled=r.enabled,
                template=r.template,
            )
            for r in rules
        ]

    async def create_notification_rule(
        self,
        event_type: str,
        slack_channel: str,
        template: str | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> NotificationRuleResponse:
        """Create a notification rule.

        Args:
            event_type: Event type
            slack_channel: Slack channel
            template: Optional template
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            Created NotificationRuleResponse DTO
        """
        rule = await self.notification_service.create_rule(
            event_type=event_type,
            slack_channel=slack_channel,
            template=template,
        )

        if user:
            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.NOTIFICATION_RULE,
                resource_id=rule.id,
                user=user,
                request=request,
                details={
                    "action": "create",
                    "event_type": event_type,
                    "slack_channel": slack_channel,
                },
            )

        await self.session.commit()
        return NotificationRuleResponse(
            id=rule.id,
            event_type=rule.event_type,
            slack_channel=rule.slack_channel,
            enabled=rule.enabled,
            template=rule.template,
        )

    async def update_notification_rule(
        self,
        rule_id: UUID,
        slack_channel: str | None = None,
        template: str | None = None,
        enabled: bool | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> NotificationRuleResponse | None:
        """Update a notification rule.

        Args:
            rule_id: Rule UUID
            slack_channel: Optional new slack channel
            template: Optional new template
            enabled: Optional new enabled state
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            Updated NotificationRuleResponse DTO or None if not found
        """
        rule = await self.notification_service.update_rule(
            rule_id,
            slack_channel=slack_channel,
            template=template,
            enabled=enabled,
        )

        if rule and user:
            changes = {}
            if slack_channel is not None:
                changes["slack_channel"] = slack_channel
            if template is not None:
                changes["template"] = template
            if enabled is not None:
                changes["enabled"] = enabled

            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.NOTIFICATION_RULE,
                resource_id=rule_id,
                user=user,
                request=request,
                details={"action": "update", "changes": changes},
            )
            await self.session.commit()

        if rule is None:
            return None

        return NotificationRuleResponse(
            id=rule.id,
            event_type=rule.event_type,
            slack_channel=rule.slack_channel,
            enabled=rule.enabled,
            template=rule.template,
        )

    async def delete_notification_rule(
        self,
        rule_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Delete a notification rule.

        Args:
            rule_id: Rule UUID
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            True if deleted, False if not found
        """
        deleted = await self.notification_service.delete_rule(rule_id)

        if deleted and user:
            await self.audit_service.log(
                action=AuditAction.SETTING_DELETE,
                resource_type=ResourceType.NOTIFICATION_RULE,
                resource_id=rule_id,
                user=user,
                request=request,
                details={"action": "delete"},
            )
            await self.session.commit()

        return deleted
