"""Email settings router for SMTP configuration."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from licence_api.dependencies import get_audit_service, get_email_service
from licence_api.models.domain.admin_user import AdminUser
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import SENSITIVE_OPERATION_LIMIT, limiter
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.email_service import (
    EmailService,
    SmtpConfigRequest,
    SmtpConfigResponse,
)

router = APIRouter()


class EmailConfigStatusResponse(BaseModel):
    """Response indicating email configuration status."""

    is_configured: bool


class TestEmailRequest(BaseModel):
    """Request to send a test email."""

    to_email: EmailStr


class TestEmailResponse(BaseModel):
    """Response from test email."""

    success: bool
    message: str


@router.get("", response_model=SmtpConfigResponse | EmailConfigStatusResponse)
async def get_email_config(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_VIEW))],
    service: Annotated[EmailService, Depends(get_email_service)],
) -> SmtpConfigResponse | EmailConfigStatusResponse:
    """Get SMTP configuration (without password).

    Returns the SMTP configuration if configured, or a status response if not.
    Password is never returned in the response.
    """
    config = await service.get_smtp_config_response()
    if config:
        return config
    return EmailConfigStatusResponse(is_configured=False)


@router.put("", response_model=SmtpConfigResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def set_email_config(
    request: Request,
    body: SmtpConfigRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[EmailService, Depends(get_email_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SmtpConfigResponse:
    """Save SMTP configuration.

    Password is encrypted before storage. If password is not provided,
    the existing password is preserved (for updating other settings).
    """
    # Check if this is new config without password
    is_new = not await service.is_configured()
    if is_new and not body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for initial SMTP configuration",
        )

    await service.save_smtp_config(body)

    config = await service.get_smtp_config_response()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save SMTP configuration",
        )

    # Audit log the configuration change
    await audit_service.log(
        action=AuditAction.SETTINGS_UPDATE,
        resource_type=ResourceType.SETTINGS,
        user=current_user,
        request=request,
        details={
            "setting": "smtp_config",
            "action": "create" if is_new else "update",
            "host": body.host,
            "port": body.port,
            "use_tls": body.use_tls,
        },
    )

    return config


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_email_config(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_DELETE))],
    service: Annotated[EmailService, Depends(get_email_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> None:
    """Delete SMTP configuration."""
    deleted = await service.delete_smtp_config()
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SMTP configuration not found",
        )

    # Audit log the deletion
    await audit_service.log(
        action=AuditAction.SETTING_DELETE,
        resource_type=ResourceType.SETTINGS,
        user=current_user,
        request=request,
        details={"setting": "smtp_config", "action": "delete"},
    )


@router.post("/test", response_model=TestEmailResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def send_test_email(
    request: Request,
    body: TestEmailRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.SETTINGS_EDIT))],
    service: Annotated[EmailService, Depends(get_email_service)],
) -> TestEmailResponse:
    """Send a test email to verify SMTP configuration."""
    success, message = await service.send_test_email(body.to_email)
    return TestEmailResponse(success=success, message=message)
