"""Payment method service for managing payment methods."""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.payment_method import (
    PaymentMethodCreate,
    PaymentMethodListResponse,
    PaymentMethodResponse,
    PaymentMethodUpdate,
)
from licence_api.repositories.payment_method_repository import PaymentMethodRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

# Valid payment method types
VALID_PAYMENT_TYPES = ["credit_card", "bank_account", "stripe", "paypal", "invoice", "other"]


class PaymentMethodService:
    """Service for managing payment methods."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.repo = PaymentMethodRepository(session)
        self.audit_service = AuditService(session)

    @staticmethod
    def _calculate_expiry_info(payment_method) -> tuple[bool, int | None]:
        """Calculate expiry info for credit cards."""
        if payment_method.type != "credit_card":
            return False, None

        details = payment_method.details or {}
        expiry_month = details.get("expiry_month")
        expiry_year = details.get("expiry_year")

        if not expiry_month or not expiry_year:
            return False, None

        today = date.today()

        try:
            # Last day of expiry month
            if int(expiry_month) == 12:
                expiry_date = date(int(expiry_year) + 1, 1, 1)
            else:
                expiry_date = date(int(expiry_year), int(expiry_month) + 1, 1)

            days_until = (expiry_date - today).days
            return days_until <= 60, days_until  # Warn 60 days before
        except (ValueError, TypeError):
            return False, None

    def _build_response(self, method) -> PaymentMethodResponse:
        """Build response from ORM model."""
        is_expiring, days_until = self._calculate_expiry_info(method)
        return PaymentMethodResponse(
            id=method.id,
            name=method.name,
            type=method.type,
            details=method.details,
            is_default=method.is_default,
            notes=method.notes,
            is_expiring=is_expiring,
            days_until_expiry=days_until,
        )

    async def list_payment_methods(self) -> PaymentMethodListResponse:
        """List all payment methods.

        Returns:
            PaymentMethodListResponse
        """
        methods = await self.repo.get_all()
        items = [self._build_response(m) for m in methods]
        return PaymentMethodListResponse(items=items, total=len(items))

    async def get_payment_method(self, payment_method_id: UUID) -> PaymentMethodResponse | None:
        """Get a payment method by ID.

        Args:
            payment_method_id: Payment method UUID

        Returns:
            PaymentMethodResponse or None if not found
        """
        method = await self.repo.get_by_id(payment_method_id)
        if method is None:
            return None
        return self._build_response(method)

    async def create_payment_method(
        self,
        data: PaymentMethodCreate,
        user: AdminUser,
        request: Request | None = None,
    ) -> PaymentMethodResponse:
        """Create a new payment method.

        Args:
            data: Payment method creation data
            user: Admin user creating the method
            request: HTTP request for audit logging

        Returns:
            Created PaymentMethodResponse

        Raises:
            ValueError: If type is invalid
        """
        if data.type not in VALID_PAYMENT_TYPES:
            raise ValueError(f"Invalid type. Must be one of: {', '.join(VALID_PAYMENT_TYPES)}")

        method = await self.repo.create(
            name=data.name,
            type=data.type,
            details=data.details,
            is_default=data.is_default,
            notes=data.notes,
        )

        if data.is_default:
            await self.repo.set_default(method.id)

        # Audit log
        await self.audit_service.log(
            action=AuditAction.PAYMENT_METHOD_CREATE,
            resource_type=ResourceType.PAYMENT_METHOD,
            resource_id=method.id,
            user=user,
            request=request,
            details={"name": data.name, "type": data.type, "is_default": data.is_default},
        )

        await self.session.commit()
        await self.session.refresh(method)

        return self._build_response(method)

    async def update_payment_method(
        self,
        payment_method_id: UUID,
        data: PaymentMethodUpdate,
        user: AdminUser,
        request: Request | None = None,
    ) -> PaymentMethodResponse:
        """Update a payment method.

        Args:
            payment_method_id: Payment method UUID
            data: Payment method update data
            user: Admin user updating the method
            request: HTTP request for audit logging

        Returns:
            Updated PaymentMethodResponse

        Raises:
            ValueError: If payment method not found
        """
        method = await self.repo.get_by_id(payment_method_id)
        if method is None:
            raise ValueError("Payment method not found")

        update_data: dict[str, Any] = {}
        changes: dict[str, Any] = {}

        if data.name is not None:
            update_data["name"] = data.name
            changes["name"] = {"old": method.name, "new": data.name}
        if data.details is not None:
            update_data["details"] = data.details
            changes["details_updated"] = True
        if data.notes is not None:
            update_data["notes"] = data.notes
            changes["notes_updated"] = True

        if update_data:
            method = await self.repo.update(payment_method_id, **update_data)

        if data.is_default:
            await self.repo.set_default(payment_method_id)
            changes["is_default"] = {"old": False, "new": True}

        # Audit log
        await self.audit_service.log(
            action=AuditAction.PAYMENT_METHOD_UPDATE,
            resource_type=ResourceType.PAYMENT_METHOD,
            resource_id=payment_method_id,
            user=user,
            request=request,
            details={"changes": changes},
        )

        await self.session.commit()
        await self.session.refresh(method)

        return self._build_response(method)

    async def delete_payment_method(
        self,
        payment_method_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> None:
        """Delete a payment method.

        Args:
            payment_method_id: Payment method UUID
            user: Admin user deleting the method
            request: HTTP request for audit logging

        Raises:
            ValueError: If payment method not found
        """
        # Get method info for audit before deletion
        method = await self.repo.get_by_id(payment_method_id)
        if method is None:
            raise ValueError("Payment method not found")

        method_name = method.name
        method_type = method.type

        deleted = await self.repo.delete(payment_method_id)
        if not deleted:
            raise ValueError("Payment method not found")

        # Audit log
        await self.audit_service.log(
            action=AuditAction.PAYMENT_METHOD_DELETE,
            resource_type=ResourceType.PAYMENT_METHOD,
            resource_id=payment_method_id,
            user=user,
            request=request,
            details={"name": method_name, "type": method_type},
        )

        await self.session.commit()
