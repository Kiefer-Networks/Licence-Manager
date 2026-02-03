"""Provider service for provider management operations."""

import uuid as uuid_module
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import PROVIDER_LOGOS_DIR
from licence_api.constants.provider_logos import get_provider_logo
from licence_api.utils.file_validation import validate_svg_content

# Logo storage configuration
LOGOS_DIR = PROVIDER_LOGOS_DIR
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2 MB
ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
IMAGE_SIGNATURES = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".webp": [b"RIFF"],
}

# HRIS providers - only one can be active at a time
HRIS_PROVIDER_NAMES = {"hibob", "personio"}
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.provider import (
    PaymentMethodSummary,
    ProviderLicenseStats,
    ProviderResponse,
)
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.encryption import get_encryption_service
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.cache_service import get_cache_service
from licence_api.services.payment_method_service import PaymentMethodService


class ProviderService:
    """Service for provider operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.provider_repo = ProviderRepository(session)
        self.license_repo = LicenseRepository(session)
        self.settings_repo = SettingsRepository(session)
        self.audit_service = AuditService(session)

    async def _get_company_domains(self) -> list[str]:
        """Get company domains from settings."""
        domains_setting = await self.settings_repo.get("company_domains")
        if domains_setting:
            return [d.lower() for d in (domains_setting.get("domains") or [])]
        return []

    async def list_providers(self) -> list[ProviderResponse]:
        """List all providers with license stats.

        Returns:
            List of ProviderResponse with license counts and stats
        """
        providers_with_counts = await self.provider_repo.get_all_with_license_counts()
        company_domains = await self._get_company_domains()
        license_stats = await self.license_repo.get_stats_by_provider(company_domains)

        items = []
        for p, count in providers_with_counts:
            pm_summary = None
            if p.payment_method:
                is_expiring, _ = PaymentMethodService._calculate_expiry_info(p.payment_method)
                pm_summary = PaymentMethodSummary(
                    id=p.payment_method.id,
                    name=p.payment_method.name,
                    type=p.payment_method.type,
                    is_expiring=is_expiring,
                )

            stats = license_stats.get(p.id, {})
            provider_stats = ProviderLicenseStats(
                active=stats.get("active", 0),
                assigned=stats.get("assigned", 0),
                external=stats.get("external", 0),
                not_in_hris=stats.get("not_in_hris", 0),
            )

            items.append(
                ProviderResponse(
                    id=p.id,
                    name=p.name,
                    display_name=p.display_name,
                    logo_url=get_provider_logo(p.name, p.logo_url),
                    enabled=p.enabled,
                    config=p.config,
                    last_sync_at=p.last_sync_at,
                    last_sync_status=p.last_sync_status,
                    license_count=count,
                    license_stats=provider_stats,
                    payment_method_id=p.payment_method_id,
                    payment_method=pm_summary,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )

        return items

    async def get_provider(self, provider_id: UUID) -> ProviderResponse | None:
        """Get provider by ID with license count.

        Args:
            provider_id: Provider UUID

        Returns:
            ProviderResponse or None if not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            return None

        counts = await self.license_repo.count_by_provider()
        license_count = counts.get(provider_id, 0)

        pm_summary = None
        if provider.payment_method:
            is_expiring, _ = PaymentMethodService._calculate_expiry_info(provider.payment_method)
            pm_summary = PaymentMethodSummary(
                id=provider.payment_method.id,
                name=provider.payment_method.name,
                type=provider.payment_method.type,
                is_expiring=is_expiring,
            )

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            logo_url=get_provider_logo(provider.name, provider.logo_url),
            enabled=provider.enabled,
            config=provider.config,
            last_sync_at=provider.last_sync_at,
            last_sync_status=provider.last_sync_status,
            license_count=license_count,
            payment_method_id=provider.payment_method_id,
            payment_method=pm_summary,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    async def create_provider(
        self,
        name: str,
        display_name: str,
        credentials: dict[str, Any],
        config: dict[str, Any] | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> ProviderResponse:
        """Create a new provider.

        Args:
            name: Provider name
            display_name: Display name
            credentials: Provider credentials
            config: Optional config
            user: Admin user creating the provider
            request: HTTP request for audit logging

        Returns:
            Created ProviderResponse

        Raises:
            ValueError: If provider already exists
        """
        existing = await self.provider_repo.get_by_name(name)
        if existing:
            raise ValueError(f"Provider {name} already configured")

        # Check if trying to add an HRIS provider when one already exists
        if name in HRIS_PROVIDER_NAMES:
            for hris_name in HRIS_PROVIDER_NAMES:
                existing_hris = await self.provider_repo.get_by_name(hris_name)
                if existing_hris:
                    raise ValueError(
                        f"Only one HRIS provider allowed. {existing_hris.display_name} is already configured."
                    )

        encryption = get_encryption_service()
        encrypted_creds = encryption.encrypt(credentials)

        provider = await self.provider_repo.create(
            name=name,
            display_name=display_name,
            credentials_encrypted=encrypted_creds,
            config=config or {},
        )

        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_CREATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider.id,
                user=user,
                request=request,
                details={
                    "name": name,
                    "display_name": display_name,
                },
            )

        # Invalidate relevant caches
        cache = await get_cache_service()
        await cache.invalidate_providers()
        await cache.invalidate_dashboard()

        await self.session.commit()

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            logo_url=get_provider_logo(provider.name, provider.logo_url),
            enabled=provider.enabled,
            config=provider.config,
            last_sync_at=provider.last_sync_at,
            last_sync_status=provider.last_sync_status,
            license_count=0,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    async def get_license_type_counts(self, provider_id: UUID) -> dict[str, int]:
        """Get license type counts for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Dict of license_type -> count
        """
        return await self.license_repo.get_license_type_counts(provider_id)

    async def get_individual_license_type_counts(self, provider_id: UUID) -> tuple[dict[str, int], bool]:
        """Get individual license type counts (extracted from combined strings).

        Args:
            provider_id: Provider UUID

        Returns:
            Tuple of (individual_counts, has_combined_types)
        """
        individual_counts = await self.license_repo.get_individual_license_type_counts(provider_id)
        raw_counts = await self.license_repo.get_license_type_counts(provider_id)
        has_combined = any("," in lt for lt in raw_counts.keys())
        return individual_counts, has_combined

    async def update_provider(
        self,
        provider_id: UUID,
        display_name: str | None = None,
        logo_url: str | None = None,
        enabled: bool | None = None,
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
        payment_method_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> ProviderResponse | None:
        """Update a provider.

        Args:
            provider_id: Provider UUID
            display_name: Optional new display name
            logo_url: Optional new logo URL
            enabled: Optional new enabled state
            config: Optional new config
            credentials: Optional new credentials
            payment_method_id: Optional new payment method ID
            user: Admin user making the update
            request: HTTP request for audit logging

        Returns:
            Updated ProviderResponse or None if not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            return None

        update_data: dict[str, Any] = {}
        changes: dict[str, Any] = {}

        if display_name is not None:
            update_data["display_name"] = display_name
            changes["display_name"] = {"old": provider.display_name, "new": display_name}

        if logo_url is not None:
            update_data["logo_url"] = logo_url if logo_url else None
            changes["logo_url"] = {"old": provider.logo_url, "new": logo_url}

        if enabled is not None:
            update_data["enabled"] = enabled
            changes["enabled"] = {"old": provider.enabled, "new": enabled}

        if config is not None:
            update_data["config"] = config
            changes["config_updated"] = True

        if credentials is not None:
            encryption = get_encryption_service()
            update_data["credentials_encrypted"] = encryption.encrypt(credentials)
            changes["credentials_updated"] = True

        if payment_method_id is not None:
            update_data["payment_method_id"] = payment_method_id
            changes["payment_method_id"] = {
                "old": str(provider.payment_method_id) if provider.payment_method_id else None,
                "new": str(payment_method_id),
            }

        if update_data:
            provider = await self.provider_repo.update(provider_id, **update_data)

            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_UPDATE,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={"changes": changes},
                )

            # Invalidate relevant caches
            cache = await get_cache_service()
            await cache.invalidate_providers()
            await cache.invalidate_dashboard()

            await self.session.commit()

        # Get license counts
        counts = await self.license_repo.count_by_provider()

        # Refresh to get payment method relationship
        await self.session.refresh(provider)

        pm_summary = None
        if provider.payment_method:
            is_expiring, _ = PaymentMethodService._calculate_expiry_info(provider.payment_method)
            pm_summary = PaymentMethodSummary(
                id=provider.payment_method.id,
                name=provider.payment_method.name,
                type=provider.payment_method.type,
                is_expiring=is_expiring,
            )

        return ProviderResponse(
            id=provider.id,
            name=provider.name,
            display_name=provider.display_name,
            logo_url=get_provider_logo(provider.name, provider.logo_url),
            enabled=provider.enabled,
            config=provider.config,
            last_sync_at=provider.last_sync_at,
            last_sync_status=provider.last_sync_status,
            license_count=counts.get(provider_id, 0),
            payment_method_id=provider.payment_method_id,
            payment_method=pm_summary,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
        )

    def _validate_logo_signature(self, content: bytes, ext: str) -> bool:
        """Validate image file signature matches extension.

        Args:
            content: File content bytes
            ext: File extension (e.g., '.png')

        Returns:
            True if signature matches or is valid SVG
        """
        ext_lower = ext.lower()
        signatures = IMAGE_SIGNATURES.get(ext_lower, [])

        # WEBP has a more complex structure
        if ext_lower == ".webp":
            if len(content) < 12:
                return False
            if not content.startswith(b"RIFF"):
                return False
            if content[8:12] != b"WEBP":
                return False
            return True

        # Special handling for SVG (text-based)
        if ext_lower == ".svg":
            header = content[:1000].lower()
            if not (b"<svg" in header or b"<?xml" in header):
                return False
            return validate_svg_content(content)

        for sig in signatures:
            if content.startswith(sig):
                return True
        return False

    async def upload_logo(
        self,
        provider_id: UUID,
        content: bytes,
        filename: str,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> str:
        """Upload a logo for a provider.

        Args:
            provider_id: Provider UUID
            content: Logo file content
            filename: Original filename
            user: Admin user making the upload
            request: HTTP request for audit logging

        Returns:
            Logo URL

        Raises:
            ValueError: If validation fails
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Validate filename and extension
        safe_filename = Path(filename).name
        ext = Path(safe_filename).suffix.lower()

        if ext not in ALLOWED_LOGO_EXTENSIONS:
            raise ValueError(
                f"File type not allowed. Allowed: {', '.join(ALLOWED_LOGO_EXTENSIONS)}"
            )

        if len(content) > MAX_LOGO_SIZE:
            raise ValueError(
                f"File too large. Maximum size: {MAX_LOGO_SIZE // 1024 // 1024}MB"
            )

        if not self._validate_logo_signature(content, ext):
            raise ValueError("File content does not match declared file type")

        # Save file
        LOGOS_DIR.mkdir(parents=True, exist_ok=True)
        stored_filename = f"{uuid_module.uuid4()}{ext}"
        file_path = LOGOS_DIR / stored_filename

        # Delete old logo if exists
        if provider.logo_url and provider.logo_url.startswith("/api/v1/providers/"):
            old_filename = provider.logo_url.split("/")[-1]
            old_path = LOGOS_DIR / old_filename
            if old_path.exists():
                old_path.unlink()

        file_path.write_bytes(content)

        # Update provider with logo URL
        logo_url = f"/api/v1/providers/{provider_id}/logo/{stored_filename}"
        await self.provider_repo.update(provider_id, logo_url=logo_url)

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={"action": "logo_upload", "filename": safe_filename},
            )

        # Invalidate caches
        cache = await get_cache_service()
        await cache.invalidate_providers()

        await self.session.commit()

        return logo_url

    async def delete_logo(
        self,
        provider_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> None:
        """Delete a provider's logo.

        Args:
            provider_id: Provider UUID
            user: Admin user making the deletion
            request: HTTP request for audit logging

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Delete file if exists
        if provider.logo_url and provider.logo_url.startswith("/api/v1/providers/"):
            old_filename = provider.logo_url.split("/")[-1]
            old_path = LOGOS_DIR / old_filename
            if old_path.exists():
                old_path.unlink()

        # Clear logo URL
        await self.provider_repo.update(provider_id, logo_url=None)

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={"action": "logo_delete"},
            )

        # Invalidate caches
        cache = await get_cache_service()
        await cache.invalidate_providers()

        await self.session.commit()

    async def delete_provider(
        self,
        provider_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> bool:
        """Delete a provider.

        Args:
            provider_id: Provider UUID
            user: Admin user making the deletion
            request: HTTP request for audit logging

        Returns:
            True if deleted, False if not found
        """
        # Get provider info for audit before deletion
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            return False

        provider_name = provider.name
        provider_display_name = provider.display_name

        deleted = await self.provider_repo.delete(provider_id)
        if not deleted:
            return False

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_DELETE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={
                    "name": provider_name,
                    "display_name": provider_display_name,
                },
            )

        # Invalidate relevant caches
        cache = await get_cache_service()
        await cache.invalidate_providers()
        await cache.invalidate_dashboard()

        await self.session.commit()

        return True
