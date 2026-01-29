"""Settings router."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.auth import get_current_user, require_admin
from licence_api.services.notification_service import NotificationService

router = APIRouter()


class SettingValue(BaseModel):
    """Setting value wrapper."""

    value: dict[str, Any]


class CompanyDomainsRequest(BaseModel):
    """Company domains request."""

    domains: list[str]


class CompanyDomainsResponse(BaseModel):
    """Company domains response."""

    domains: list[str]


class NotificationRuleCreate(BaseModel):
    """Create notification rule request."""

    event_type: str
    slack_channel: str
    template: str | None = None


class NotificationRuleUpdate(BaseModel):
    """Update notification rule request."""

    slack_channel: str | None = None
    template: str | None = None
    enabled: bool | None = None


class NotificationRuleResponse(BaseModel):
    """Notification rule response."""

    id: UUID
    event_type: str
    slack_channel: str
    enabled: bool
    template: str | None = None


class SetupStatusResponse(BaseModel):
    """Setup status response."""

    is_complete: bool
    has_hibob: bool
    has_providers: bool
    has_admin: bool


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SetupStatusResponse:
    """Get setup status (no auth required for initial setup)."""
    from licence_api.repositories.provider_repository import ProviderRepository
    from licence_api.repositories.user_repository import UserRepository

    provider_repo = ProviderRepository(db)
    user_repo = UserRepository(db)

    has_any_provider = await provider_repo.exists_any()
    hibob = await provider_repo.get_by_name("hibob")
    admin_count = await user_repo.count_admins()

    return SetupStatusResponse(
        is_complete=has_any_provider and hibob is not None and admin_count > 0,
        has_hibob=hibob is not None,
        has_providers=has_any_provider,
        has_admin=admin_count > 0,
    )


@router.get("", response_model=dict[str, Any])
async def get_all_settings(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get all application settings."""
    repo = SettingsRepository(db)
    return await repo.get_all()


@router.get("/company-domains", response_model=CompanyDomainsResponse)
async def get_company_domains(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyDomainsResponse:
    """Get configured company domains."""
    repo = SettingsRepository(db)
    setting = await repo.get("company_domains")
    if setting is None:
        return CompanyDomainsResponse(domains=[])
    return CompanyDomainsResponse(domains=setting.get("domains", []))


@router.put("/company-domains", response_model=CompanyDomainsResponse)
async def set_company_domains(
    request: CompanyDomainsRequest,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyDomainsResponse:
    """Set company domains. Admin only."""
    repo = SettingsRepository(db)
    # Normalize domains (lowercase, strip whitespace)
    domains = [d.strip().lower() for d in request.domains if d.strip()]
    await repo.set("company_domains", {"domains": domains})
    await db.commit()
    return CompanyDomainsResponse(domains=domains)


@router.get("/{key}", response_model=dict[str, Any] | None)
async def get_setting(
    key: str,
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any] | None:
    """Get a specific setting by key."""
    repo = SettingsRepository(db)
    return await repo.get(key)


@router.put("/{key}", response_model=dict[str, Any])
async def set_setting(
    key: str,
    request: SettingValue,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Set a setting value. Admin only."""
    repo = SettingsRepository(db)
    await repo.set(key, request.value)
    return request.value


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(
    key: str,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a setting. Admin only."""
    repo = SettingsRepository(db)
    deleted = await repo.delete(key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found",
        )


# Notification rules
@router.get("/notifications/rules", response_model=list[NotificationRuleResponse])
async def list_notification_rules(
    current_user: Annotated[AdminUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NotificationRuleResponse]:
    """List all notification rules."""
    service = NotificationService(db)
    rules = await service.get_rules()
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
    request: NotificationRuleCreate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRuleResponse:
    """Create a notification rule. Admin only."""
    service = NotificationService(db)
    rule = await service.create_rule(
        event_type=request.event_type,
        slack_channel=request.slack_channel,
        template=request.template,
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
    rule_id: UUID,
    request: NotificationRuleUpdate,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NotificationRuleResponse:
    """Update a notification rule. Admin only."""
    service = NotificationService(db)
    rule = await service.update_rule(
        rule_id,
        slack_channel=request.slack_channel,
        template=request.template,
        enabled=request.enabled,
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
    rule_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a notification rule. Admin only."""
    service = NotificationService(db)
    deleted = await service.delete_rule(rule_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification rule not found",
        )
