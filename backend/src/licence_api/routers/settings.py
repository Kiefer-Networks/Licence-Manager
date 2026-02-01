"""Settings router."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.auth import get_current_user, require_admin, require_permission, Permissions
from licence_api.security.rate_limit import limiter
from licence_api.services.notification_service import NotificationService
from licence_api.services.settings_service import SettingsService

router = APIRouter()


class SettingValue(BaseModel):
    """Setting value wrapper."""

    value: dict[str, Any]


class CompanyDomainsRequest(BaseModel):
    """Company domains request."""

    domains: list[str] = Field(max_length=100)  # Max 100 domains

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v: list[str]) -> list[str]:
        """Validate each domain has max length."""
        for domain in v:
            if len(domain) > 255:
                raise ValueError("Each domain must be max 255 characters")
        return v


class CompanyDomainsResponse(BaseModel):
    """Company domains response."""

    domains: list[str]


class ThresholdSettings(BaseModel):
    """Threshold settings for warnings and notifications."""

    inactive_days: int = Field(default=30, ge=1, le=365)
    expiring_days: int = Field(default=90, ge=1, le=365)
    low_utilization_percent: int = Field(default=70, ge=0, le=100)
    cost_increase_percent: int = Field(default=20, ge=0, le=1000)
    max_unassigned_licenses: int = Field(default=10, ge=0, le=10000)


DEFAULT_THRESHOLDS = ThresholdSettings()


class NotificationRuleCreate(BaseModel):
    """Create notification rule request."""

    event_type: str = Field(max_length=100)
    slack_channel: str = Field(max_length=255)
    template: str | None = Field(default=None, max_length=5000)


class NotificationRuleUpdate(BaseModel):
    """Update notification rule request."""

    slack_channel: str | None = Field(default=None, max_length=255)
    template: str | None = Field(default=None, max_length=5000)
    enabled: bool | None = None


class NotificationRuleResponse(BaseModel):
    """Notification rule response."""

    id: UUID
    event_type: str
    slack_channel: str
    enabled: bool
    template: str | None = None


class SetupStatusResponse(BaseModel):
    """Setup status response (public - minimal info)."""

    is_complete: bool


class SetupStatusDetailedResponse(BaseModel):
    """Detailed setup status response (authenticated)."""

    is_complete: bool
    has_hibob: bool
    has_providers: bool
    has_admin: bool


class TestNotificationRequest(BaseModel):
    """Test notification request."""

    channel: str


class TestNotificationResponse(BaseModel):
    """Test notification response."""

    success: bool
    message: str


# Dependency injection
def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    """Get SettingsService instance."""
    return SettingsService(db)


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    """Get NotificationService instance."""
    return NotificationService(db)


@router.get("/status", response_model=SetupStatusResponse)
@limiter.limit("30/minute")
async def get_setup_status(
    request: Request,
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SetupStatusResponse:
    """Get basic setup status.

    This is a public endpoint - no authentication required.
    Rate limited to prevent abuse.
    """
    status = await service.get_setup_status()
    return SetupStatusResponse(is_complete=status.is_complete)


@router.get("/status/detailed", response_model=SetupStatusDetailedResponse)
async def get_setup_status_detailed(
    current_user: Annotated[AdminUser, Depends(require_admin)],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> SetupStatusDetailedResponse:
    """Get detailed setup status. Admin only."""
    status = await service.get_setup_status(detailed=True)
    return SetupStatusDetailedResponse(
        is_complete=status.is_complete,
        has_hibob=status.has_hibob,
        has_providers=status.has_providers,
        has_admin=status.has_admin,
    )


@router.get("", response_model=dict[str, Any])
async def get_all_settings(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> dict[str, Any]:
    """Get all application settings. Requires settings.view permission."""
    return await service.get_all()


@router.get("/company-domains", response_model=CompanyDomainsResponse)
async def get_company_domains(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> CompanyDomainsResponse:
    """Get configured company domains. Requires settings.view permission."""
    setting = await service.get("company_domains")
    if setting is None:
        return CompanyDomainsResponse(domains=[])
    return CompanyDomainsResponse(domains=setting.get("domains", []))


@router.put("/company-domains", response_model=CompanyDomainsResponse)
async def set_company_domains(
    http_request: Request,
    request: CompanyDomainsRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> CompanyDomainsResponse:
    """Set company domains. Requires settings.edit permission."""
    domains = await service.set_company_domains(
        domains=request.domains,
        user=current_user,
        request=http_request,
    )
    return CompanyDomainsResponse(domains=domains)


@router.get("/thresholds", response_model=ThresholdSettings)
async def get_threshold_settings(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> ThresholdSettings:
    """Get threshold settings for warnings and notifications."""
    settings = await service.get("thresholds")
    if settings is None:
        return DEFAULT_THRESHOLDS
    return ThresholdSettings(**settings)


@router.put("/thresholds", response_model=ThresholdSettings)
async def update_threshold_settings(
    http_request: Request,
    request: ThresholdSettings,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> ThresholdSettings:
    """Update threshold settings."""
    await service.set_thresholds(
        thresholds=request.model_dump(),
        user=current_user,
        request=http_request,
    )
    return request


@router.get("/{key}", response_model=dict[str, Any] | None)
async def get_setting(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
    key: str = Path(max_length=100, pattern=r"^[a-z][a-z0-9_]*$"),
) -> dict[str, Any] | None:
    """Get a specific setting by key. Requires settings.view permission."""
    return await service.get(key)


@router.put("/{key}", response_model=dict[str, Any])
async def set_setting(
    http_request: Request,
    request: SettingValue,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
    key: str = Path(max_length=100, pattern=r"^[a-z][a-z0-9_]*$"),
) -> dict[str, Any]:
    """Set a setting value. Requires settings.edit permission."""
    return await service.set(
        key=key,
        value=request.value,
        user=current_user,
        request=http_request,
    )


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    http_request: Request,
    key: str,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> None:
    """Delete a setting. Requires settings.edit permission."""
    deleted = await service.delete(
        key=key,
        user=current_user,
        request=http_request,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )


@router.get("/notifications/rules", response_model=list[NotificationRuleResponse])
async def list_notification_rules(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> list[NotificationRuleResponse]:
    """List all notification rules. Requires settings.view permission."""
    rules = await service.get_notification_rules()
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


@router.post(
    "/notifications/rules",
    response_model=NotificationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_rule(
    http_request: Request,
    request: NotificationRuleCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> NotificationRuleResponse:
    """Create a notification rule. Requires settings.edit permission."""
    rule = await service.create_notification_rule(
        event_type=request.event_type,
        slack_channel=request.slack_channel,
        template=request.template,
        user=current_user,
        request=http_request,
    )
    return NotificationRuleResponse(
        id=rule.id,
        event_type=rule.event_type,
        slack_channel=rule.slack_channel,
        enabled=rule.enabled,
        template=rule.template,
    )


@router.put("/notifications/rules/{rule_id}", response_model=NotificationRuleResponse)
async def update_notification_rule(
    http_request: Request,
    rule_id: UUID,
    request: NotificationRuleUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> NotificationRuleResponse:
    """Update a notification rule. Requires settings.edit permission."""
    rule = await service.update_notification_rule(
        rule_id=rule_id,
        slack_channel=request.slack_channel,
        template=request.template,
        enabled=request.enabled,
        user=current_user,
        request=http_request,
    )
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification rule not found",
        )
    return NotificationRuleResponse(
        id=rule.id,
        event_type=rule.event_type,
        slack_channel=rule.slack_channel,
        enabled=rule.enabled,
        template=rule.template,
    )


@router.delete("/notifications/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification_rule(
    http_request: Request,
    rule_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[SettingsService, Depends(get_settings_service)],
) -> None:
    """Delete a notification rule. Requires settings.edit permission."""
    deleted = await service.delete_notification_rule(
        rule_id=rule_id,
        user=current_user,
        request=http_request,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification rule not found",
        )


@router.post("/notifications/test", response_model=TestNotificationResponse)
async def test_slack_notification(
    request: TestNotificationRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    notification_service: Annotated[NotificationService, Depends(get_notification_service)],
) -> TestNotificationResponse:
    """Send a test notification to Slack. Requires settings.edit permission."""
    slack_config = await settings_service.get("slack")

    if not slack_config or not slack_config.get("bot_token"):
        return TestNotificationResponse(
            success=False,
            message="Slack bot token not configured. Please configure Slack settings first.",
        )

    bot_token = slack_config["bot_token"]

    success, message = await notification_service.send_test_notification(
        channel=request.channel,
        token=bot_token,
    )

    return TestNotificationResponse(success=success, message=message)
