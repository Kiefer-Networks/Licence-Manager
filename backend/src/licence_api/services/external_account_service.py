"""External account service for managing employee provider links."""

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.external_account import (
    EmployeeLookupResponse,
    ExternalAccountListResponse,
    ExternalAccountResponse,
)
from licence_api.repositories.employee_external_account_repository import (
    EmployeeExternalAccountRepository,
)
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

# Setting key for enabling/disabling username matching
SETTING_USERNAME_MATCHING_ENABLED = "username_matching_enabled"


class ExternalAccountService:
    """Service for managing external account links."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.external_account_repo = EmployeeExternalAccountRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.settings_repo = SettingsRepository(session)
        self.audit_service = AuditService(session)

    async def is_username_matching_enabled(self) -> bool:
        """Check if username matching feature is enabled.

        Returns:
            True if enabled (default), False if disabled
        """
        setting = await self.settings_repo.get(SETTING_USERNAME_MATCHING_ENABLED)
        if setting is None:
            return True  # Enabled by default
        return setting.get("enabled", True)

    async def set_username_matching_enabled(
        self,
        enabled: bool,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Enable or disable username matching.

        Args:
            enabled: Whether to enable the feature
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            The new enabled state
        """
        await self.settings_repo.set(
            SETTING_USERNAME_MATCHING_ENABLED,
            {"enabled": enabled},
        )

        if user:
            await self.audit_service.log(
                action=AuditAction.SETTING_UPDATE,
                resource_type=ResourceType.SETTING,
                resource_id=SETTING_USERNAME_MATCHING_ENABLED,
                user=user,
                request=request,
                details={"enabled": enabled},
            )

        await self.session.commit()
        return enabled

    async def get_employee_external_accounts(
        self,
        employee_id: UUID,
    ) -> ExternalAccountListResponse:
        """Get all external accounts for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            ExternalAccountListResponse with account DTOs and total count
        """
        accounts = await self.external_account_repo.get_by_employee(employee_id)
        account_dtos = [
            ExternalAccountResponse.model_validate(acc) for acc in accounts
        ]
        return ExternalAccountListResponse(accounts=account_dtos, total=len(account_dtos))

    async def link_account(
        self,
        employee_id: UUID,
        provider_type: str,
        external_username: str,
        external_user_id: str | None = None,
        display_name: str | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> ExternalAccountResponse:
        """Link an external account to an employee.

        Args:
            employee_id: Employee UUID
            provider_type: Provider type (e.g., "huggingface")
            external_username: Username in the external system
            external_user_id: Optional ID in the external system
            display_name: Optional display name from external system
            user: Admin user creating the link
            request: HTTP request for audit logging

        Returns:
            ExternalAccountResponse DTO for the created/existing link

        Raises:
            ValueError: If employee not found or username already linked
        """
        # Verify employee exists
        employee = await self.employee_repo.get_by_id(employee_id)
        if employee is None:
            raise ValueError(f"Employee not found: {employee_id}")

        # Check if username is already linked
        existing = await self.external_account_repo.get_by_provider_and_username(
            provider_type, external_username
        )
        if existing:
            if existing.employee_id == employee_id:
                # Already linked to this employee, return existing
                return ExternalAccountResponse.model_validate(existing)
            raise ValueError(
                f"Username '{external_username}' is already linked to another employee"
            )

        # Create the link
        account = await self.external_account_repo.link_account(
            employee_id=employee_id,
            provider_type=provider_type,
            external_username=external_username,
            external_user_id=external_user_id,
            display_name=display_name,
            linked_by_id=user.id if user else None,
        )

        if user:
            await self.audit_service.log(
                action=AuditAction.EXTERNAL_ACCOUNT_LINK,
                resource_type=ResourceType.EMPLOYEE,
                resource_id=employee_id,
                user=user,
                request=request,
                details={
                    "provider_type": provider_type,
                    "external_username": external_username,
                    "external_user_id": external_user_id,
                },
            )

        await self.session.commit()
        return ExternalAccountResponse.model_validate(account)

    async def unlink_account(
        self,
        provider_type: str,
        external_username: str,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Unlink an external account.

        Args:
            provider_type: Provider type
            external_username: Username in the external system
            user: Admin user removing the link
            request: HTTP request for audit logging

        Returns:
            True if deleted, False if not found
        """
        # Get account for audit logging
        account = await self.external_account_repo.get_by_provider_and_username(
            provider_type, external_username
        )
        if account is None:
            return False

        employee_id = account.employee_id

        deleted = await self.external_account_repo.unlink_account(provider_type, external_username)

        if deleted and user:
            await self.audit_service.log(
                action=AuditAction.EXTERNAL_ACCOUNT_UNLINK,
                resource_type=ResourceType.EMPLOYEE,
                resource_id=employee_id,
                user=user,
                request=request,
                details={
                    "provider_type": provider_type,
                    "external_username": external_username,
                },
            )
            await self.session.commit()

        return deleted

    async def unlink_account_by_id(
        self,
        account_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Unlink an external account by its ID.

        Args:
            account_id: External account UUID
            user: Admin user removing the link
            request: HTTP request for audit logging

        Returns:
            True if deleted, False if not found
        """
        account = await self.external_account_repo.get_by_id(account_id)
        if account is None:
            return False

        return await self.unlink_account(
            account.provider_type,
            account.external_username,
            user=user,
            request=request,
        )

    async def bulk_link_accounts(
        self,
        links: list,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Bulk link multiple external accounts.

        Iterates over the provided links, calling link_account() for each.
        Categorizes results into linked, skipped (already linked), and errors.

        Args:
            links: List of link objects with employee_id, provider_type,
                   external_username, external_user_id, display_name
            user: Admin user creating the links
            request: HTTP request for audit logging

        Returns:
            Dict with linked count, skipped count, and error messages
        """
        linked = 0
        skipped = 0
        errors: list[str] = []

        for link in links:
            try:
                await self.link_account(
                    employee_id=link.employee_id,
                    provider_type=link.provider_type,
                    external_username=link.external_username,
                    external_user_id=link.external_user_id,
                    display_name=link.display_name,
                    user=user,
                    request=request,
                )
                linked += 1
            except ValueError as e:
                if "already linked" in str(e).lower():
                    skipped += 1
                else:
                    errors.append(f"{link.external_username}: {str(e)}")

        return {"linked": linked, "skipped": skipped, "errors": errors}

    async def get_employee_by_external_username(
        self,
        provider_type: str,
        external_username: str,
    ) -> EmployeeLookupResponse | None:
        """Get employee by their external username.

        Args:
            provider_type: Provider type
            external_username: Username in the external system

        Returns:
            EmployeeLookupResponse DTO or None if not found
        """
        employee = await self.external_account_repo.get_employee_by_external_username(
            provider_type, external_username
        )
        if employee is None:
            return None
        return EmployeeLookupResponse(
            employee_id=str(employee.id),
            email=employee.email,
            full_name=employee.full_name,
            department=employee.department,
        )

    async def find_employee_suggestions(
        self,
        display_name: str,
        provider_type: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find employee suggestions based on name similarity.

        Args:
            display_name: Name to match against
            provider_type: Provider type (to exclude already linked employees)
            limit: Maximum number of suggestions

        Returns:
            List of suggestion dicts with employee info and confidence score
        """
        if not await self.is_username_matching_enabled():
            return []

        suggestions = await self.external_account_repo.find_employee_suggestions(
            display_name, provider_type, limit
        )

        return [
            {
                "employee_id": str(emp.id),
                "email": emp.email,
                "full_name": emp.full_name,
                "department": emp.department,
                "confidence": round(score, 2),
            }
            for emp, score in suggestions
        ]

    async def bulk_lookup(
        self,
        provider_type: str,
        usernames: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Lookup multiple usernames at once.

        Args:
            provider_type: Provider type
            usernames: List of usernames to lookup

        Returns:
            Dict mapping username to employee info
        """
        employees = await self.external_account_repo.bulk_lookup(provider_type, usernames)

        return {
            username: {
                "employee_id": str(emp.id),
                "email": emp.email,
                "full_name": emp.full_name,
                "department": emp.department,
            }
            for username, emp in employees.items()
        }

    async def get_all_for_provider(
        self,
        provider_type: str,
    ) -> dict[str, str]:
        """Get all username->employee_id mappings for a provider.

        Args:
            provider_type: Provider type

        Returns:
            Dict mapping external_username to employee_id (as string)
        """
        mappings = await self.external_account_repo.get_all_for_provider(provider_type)
        return {username: str(emp_id) for username, emp_id in mappings.items()}
