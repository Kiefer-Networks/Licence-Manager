"""Providers router."""

import copy
import uuid as uuid_module
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import LOGOS_DIR
from licence_api.constants.provider_logos import get_provider_logo
from licence_api.database import get_db
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.provider import ProviderName
from licence_api.models.dto.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderListResponse,
    PaymentMethodSummary,
)
from licence_api.services.payment_method_service import PaymentMethodService
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import get_current_user, require_permission, Permissions
from licence_api.security.csrf import CSRFProtected
from licence_api.security.encryption import get_encryption_service
from licence_api.security.rate_limit import limiter, PROVIDER_TEST_CONNECTION_LIMIT, SENSITIVE_OPERATION_LIMIT
from licence_api.services.audit_service import AuditService, AuditAction, ResourceType
from licence_api.services.cache_service import get_cache_service
from licence_api.services.pricing_service import PricingService
from licence_api.services.provider_service import ProviderService
from licence_api.services.sync_service import SyncService
from licence_api.utils.file_validation import validate_svg_content
from licence_api.middleware.error_handler import sanitize_error_for_audit

router = APIRouter()

# Use centralized rate limits
TEST_CONNECTION_LIMIT = PROVIDER_TEST_CONNECTION_LIMIT
SYNC_LIMIT = SENSITIVE_OPERATION_LIMIT


# Dependency injection functions
def get_provider_repository(db: AsyncSession = Depends(get_db)) -> ProviderRepository:
    """Get ProviderRepository instance."""
    return ProviderRepository(db)


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    """Get AuditService instance."""
    return AuditService(db)


def get_sync_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    """Get SyncService instance."""
    return SyncService(db)


def get_pricing_service(db: AsyncSession = Depends(get_db)) -> PricingService:
    """Get PricingService instance."""
    return PricingService(db)


def get_provider_service(db: AsyncSession = Depends(get_db)) -> ProviderService:
    """Get ProviderService instance."""
    return ProviderService(db)


class TestConnectionRequest(BaseModel):
    """Request to test provider connection."""

    name: str  # Allow any provider name (including 'manual')
    credentials: dict[str, Any]


class TestConnectionResponse(BaseModel):
    """Response from connection test."""

    success: bool
    message: str


class SyncResponse(BaseModel):
    """Response from sync operation."""

    success: bool
    results: dict[str, Any]


@router.get("", response_model=ProviderListResponse)
async def list_providers(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderListResponse:
    """List all configured providers. Requires providers.view permission."""
    items = await provider_service.list_providers()
    return ProviderListResponse(items=items, total=len(items))


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Get a single provider by ID. Requires providers.view permission."""
    provider = await provider_service.get_provider(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    return provider


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    http_request: Request,
    request: ProviderCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_CREATE))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Create a new provider. Requires providers.create permission."""
    try:
        return await provider_service.create_provider(
            name=request.name,
            display_name=request.display_name,
            credentials=request.credentials,
            config=request.config,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider with this name already exists or configuration is invalid",
        )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    http_request: Request,
    provider_id: UUID,
    request: ProviderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Update a provider. Requires providers.edit permission."""
    result = await provider_service.update_provider(
        provider_id=provider_id,
        display_name=request.display_name,
        logo_url=request.logo_url,
        enabled=request.enabled,
        config=request.config,
        credentials=request.credentials,
        payment_method_id=request.payment_method_id,
        user=current_user,
        request=http_request,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    return result


ALLOWED_LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB

# Logo file signatures
LOGO_SIGNATURES = {
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".webp": [b"RIFF"],
    ".svg": [b"<?xml", b"<svg", b"\xef\xbb\xbf<?xml", b"\xef\xbb\xbf<svg"],
}


def validate_logo_signature(content: bytes, extension: str) -> bool:
    """Validate logo file content matches expected signature.

    For SVG files, also validates that the content doesn't contain
    dangerous elements like scripts or event handlers.
    """
    ext_lower = extension.lower()
    signatures = LOGO_SIGNATURES.get(ext_lower)
    if not signatures:
        return False

    # Special handling for WEBP
    if ext_lower == ".webp":
        if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":
            return True
        return False

    # Special handling for SVG (text-based)
    if ext_lower == ".svg":
        # Check first 1000 bytes for SVG indicators
        header = content[:1000].lower()
        if not (b"<svg" in header or b"<?xml" in header):
            return False
        # Validate SVG content for dangerous elements
        return validate_svg_content(content)

    for sig in signatures:
        if content.startswith(sig):
            return True
    return False


class LogoUploadResponse(BaseModel):
    """Logo upload response."""
    logo_url: str


@router.post("/{provider_id}/logo", response_model=LogoUploadResponse)
async def upload_provider_logo(
    http_request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    _csrf: Annotated[None, Depends(CSRFProtected())],
    file: UploadFile = File(...),
) -> LogoUploadResponse:
    """Upload a logo for a provider. Requires providers.edit permission.

    Note: CSRF protection is explicitly applied via CSRFProtected dependency
    for file upload endpoints, providing consistent validation pattern.
    """
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    content = await file.read()

    try:
        logo_url = await provider_service.upload_logo(
            provider_id=provider_id,
            content=content,
            filename=file.filename,
            user=current_user,
            request=http_request,
        )
        return LogoUploadResponse(logo_url=logo_url)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid logo file",
        )


@router.get("/{provider_id}/logo/{filename}")
async def get_provider_logo_file(
    provider_id: UUID,
    filename: str,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
) -> FileResponse:
    """Get a provider's logo file."""
    # Sanitize filename
    safe_filename = Path(filename).name
    if "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    file_path = LOGOS_DIR / safe_filename

    # Validate path is within LOGOS_DIR
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(LOGOS_DIR.resolve()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
    except (ValueError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Logo not found",
        )

    # Determine media type
    ext = file_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(path=file_path, media_type=media_type)


@router.delete("/{provider_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_logo(
    http_request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> None:
    """Delete a provider's logo. Requires providers.edit permission."""
    try:
        await provider_service.delete_logo(
            provider_id=provider_id,
            user=current_user,
            request=http_request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider or logo not found",
        )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    http_request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_DELETE))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> None:
    """Delete a provider. Requires providers.delete permission."""
    deleted = await provider_service.delete_provider(
        provider_id=provider_id,
        user=current_user,
        request=http_request,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )


@router.post("/test-connection", response_model=TestConnectionResponse)
@limiter.limit(TEST_CONNECTION_LIMIT)
async def test_provider_connection(
    request: Request,
    body: TestConnectionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_CREATE))],
) -> TestConnectionResponse:
    """Test provider connection with given credentials. Requires providers.create permission.

    Security Note (INJ-03): SSRF risk is mitigated by using a hardcoded allowlist of
    provider classes. External API URLs are defined within each provider class, not
    by user input. User-provided credentials are only used for authentication.
    """
    # Manual providers don't need connection test
    if body.name == "manual":
        return TestConnectionResponse(
            success=True,
            message="Manual provider - no connection test needed",
        )

    from licence_api.providers import (
        AdobeProvider,
        AnthropicProvider,
        AtlassianProvider,
        Auth0Provider,
        HiBobProvider,
        GoogleWorkspaceProvider,
        MailjetProvider,
        MicrosoftProvider,
        OpenAIProvider,
        FigmaProvider,
        CursorProvider,
        SlackProvider,
        JetBrainsProvider,
    )

    providers = {
        ProviderName.ADOBE: AdobeProvider,
        ProviderName.ANTHROPIC: AnthropicProvider,
        ProviderName.ATLASSIAN: AtlassianProvider,
        ProviderName.AUTH0: Auth0Provider,
        ProviderName.HIBOB: HiBobProvider,
        ProviderName.GOOGLE_WORKSPACE: GoogleWorkspaceProvider,
        ProviderName.MAILJET: MailjetProvider,
        ProviderName.MICROSOFT: MicrosoftProvider,
        ProviderName.OPENAI: OpenAIProvider,
        ProviderName.FIGMA: FigmaProvider,
        ProviderName.CURSOR: CursorProvider,
        ProviderName.SLACK: SlackProvider,
        ProviderName.JETBRAINS: JetBrainsProvider,
    }

    provider_class = providers.get(ProviderName(body.name) if body.name in [e.value for e in ProviderName] else None)
    if provider_class is None:
        return TestConnectionResponse(
            success=False,
            message=f"Unknown provider: {body.name}",
        )

    try:
        provider = provider_class(body.credentials)
        success = await provider.test_connection()
        return TestConnectionResponse(
            success=success,
            message="Connection successful" if success else "Connection failed",
        )
    except (ValueError, KeyError, TypeError):
        return TestConnectionResponse(
            success=False,
            message="Invalid provider configuration. Please check your credentials.",
        )
    except (ConnectionError, TimeoutError, OSError):
        return TestConnectionResponse(
            success=False,
            message="Connection failed. Please verify your credentials and network.",
        )


@router.post("/sync", response_model=SyncResponse)
@limiter.limit(SYNC_LIMIT)
async def trigger_sync(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    provider_id: UUID | None = None,
) -> SyncResponse:
    """Trigger a sync operation. Requires providers.sync permission."""
    try:
        results = await sync_service.trigger_sync(provider_id)

        # Audit log
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"results": results, "scope": "single" if provider_id else "all"},
        )

        # Invalidate caches after sync (data has changed)
        cache = await get_cache_service()
        await cache.invalidate_all()

        return SyncResponse(success=True, results=results)
    except (ConnectionError, TimeoutError, OSError) as e:
        # Network/connection errors - audit and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"success": False, "error_code": "CONNECTION_ERROR", "error_type": type(e).__name__},
        )
        return SyncResponse(success=False, results={"error": "Connection to provider failed"})
    except ValueError as e:
        # Validation errors - audit and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"success": False, "error_code": "VALIDATION_ERROR", "error_type": "ValueError"},
        )
        return SyncResponse(success=False, results={"error": "Invalid provider configuration"})
    except Exception as e:
        # Unexpected errors - audit with sanitized details and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"success": False, **sanitize_error_for_audit(e)},
        )
        return SyncResponse(success=False, results={"error": "Sync operation failed"})


@router.post("/{provider_id}/sync", response_model=SyncResponse)
@limiter.limit(SYNC_LIMIT)
async def sync_provider(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
) -> SyncResponse:
    """Sync a specific provider. Requires providers.sync permission."""
    try:
        results = await sync_service.sync_provider(provider_id)

        # Audit log
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"results": results},
        )

        # Invalidate caches after sync (data has changed)
        cache = await get_cache_service()
        await cache.invalidate_all()

        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    except (ConnectionError, TimeoutError, OSError) as e:
        # Network/connection errors - audit and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"success": False, "error_code": "CONNECTION_ERROR", "error_type": type(e).__name__},
        )
        return SyncResponse(success=False, results={"error": "Connection to provider failed"})
    except Exception as e:
        # Unexpected errors - audit with sanitized details and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=provider_id,
            user=current_user,
            request=request,
            details={"success": False, **sanitize_error_for_audit(e)},
        )
        return SyncResponse(success=False, results={"error": "Sync operation failed"})


class LicenseTypePricing(BaseModel):
    """License type pricing configuration."""

    license_type: str
    display_name: str | None = None  # Custom display name (e.g., "Microsoft 365 E5" instead of "SKU_E5")
    cost: str  # Cost per billing cycle
    currency: str = "EUR"
    billing_cycle: str = "yearly"  # yearly, monthly, perpetual, one_time
    payment_frequency: str = "yearly"  # yearly, monthly, one_time (how often you pay)
    next_billing_date: str | None = None  # ISO date string
    notes: str | None = None  # e.g., "Includes support", "Volume discount"


class PackagePricing(BaseModel):
    """Package pricing for providers with bulk/package licenses (e.g., Mattermost)."""

    cost: str  # Total package cost
    currency: str = "EUR"
    billing_cycle: str = "yearly"  # yearly, monthly
    next_billing_date: str | None = None
    notes: str | None = None


class LicenseTypePricingResponse(BaseModel):
    """Response with all license type pricing."""

    pricing: list[LicenseTypePricing]
    package_pricing: PackagePricing | None = None


class LicenseTypePricingRequest(BaseModel):
    """Request to update license type pricing."""

    pricing: list[LicenseTypePricing]
    package_pricing: PackagePricing | None = None


class LicenseTypeInfo(BaseModel):
    """Info about a license type."""

    license_type: str
    count: int
    pricing: LicenseTypePricing | None = None


class LicenseTypesResponse(BaseModel):
    """Response with all license types for a provider."""

    license_types: list[LicenseTypeInfo]


@router.get("/{provider_id}/license-types", response_model=LicenseTypesResponse)
async def get_provider_license_types(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> LicenseTypesResponse:
    """Get all license types for a provider with their counts and current pricing. Requires providers.view permission."""
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Get license type counts
    type_counts = await provider_service.get_license_type_counts(provider_id)

    # Get current pricing from config
    pricing_config = (provider.config or {}).get("license_pricing", {})

    license_types = []
    for license_type, count in type_counts.items():
        price_info = pricing_config.get(license_type)
        pricing = None
        if price_info:
            pricing = LicenseTypePricing(
                license_type=license_type,
                display_name=price_info.get("display_name"),
                cost=price_info.get("cost", "0"),
                currency=price_info.get("currency", "EUR"),
                billing_cycle=price_info.get("billing_cycle", "yearly"),
                payment_frequency=price_info.get("payment_frequency", "yearly"),
                next_billing_date=price_info.get("next_billing_date"),
                notes=price_info.get("notes"),
            )
        license_types.append(
            LicenseTypeInfo(
                license_type=license_type,
                count=count,
                pricing=pricing,
            )
        )

    # Sort by count descending
    license_types.sort(key=lambda x: x.count, reverse=True)

    return LicenseTypesResponse(license_types=license_types)


@router.get("/{provider_id}/pricing", response_model=LicenseTypePricingResponse)
async def get_provider_pricing(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
) -> LicenseTypePricingResponse:
    """Get license type pricing for a provider. Requires providers.view permission."""
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    pricing_config = (provider.config or {}).get("license_pricing", {})
    pricing = [
        LicenseTypePricing(
            license_type=lt,
            display_name=info.get("display_name"),
            cost=info.get("cost", "0"),
            currency=info.get("currency", "EUR"),
            billing_cycle=info.get("billing_cycle", "yearly"),
            payment_frequency=info.get("payment_frequency", "yearly"),
            next_billing_date=info.get("next_billing_date"),
            notes=info.get("notes"),
        )
        for lt, info in pricing_config.items()
    ]

    # Get package pricing if exists
    package_pricing_config = (provider.config or {}).get("package_pricing")
    package_pricing = None
    if package_pricing_config:
        package_pricing = PackagePricing(
            cost=package_pricing_config.get("cost", "0"),
            currency=package_pricing_config.get("currency", "EUR"),
            billing_cycle=package_pricing_config.get("billing_cycle", "yearly"),
            next_billing_date=package_pricing_config.get("next_billing_date"),
            notes=package_pricing_config.get("notes"),
        )

    return LicenseTypePricingResponse(pricing=pricing, package_pricing=package_pricing)


@router.put("/{provider_id}/pricing", response_model=LicenseTypePricingResponse)
async def update_provider_pricing(
    http_request: Request,
    provider_id: UUID,
    request: LicenseTypePricingRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> LicenseTypePricingResponse:
    """Update license type pricing for a provider. Requires providers.edit permission."""
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Build pricing config
    pricing_config = PricingService.build_pricing_config_dict(request.pricing)

    # Build package pricing config
    package_pricing = None
    if request.package_pricing and request.package_pricing.cost:
        package_pricing = {
            "cost": request.package_pricing.cost,
            "currency": request.package_pricing.currency,
            "billing_cycle": request.package_pricing.billing_cycle,
            "next_billing_date": request.package_pricing.next_billing_date,
            "notes": request.package_pricing.notes,
        }

    # Use pricing service to update (handles audit logging and commit)
    await pricing_service.update_license_pricing(
        provider_id=provider_id,
        pricing_config=pricing_config,
        package_pricing=package_pricing,
        user=current_user,
        request=http_request,
    )

    return LicenseTypePricingResponse(
        pricing=request.pricing,
        package_pricing=request.package_pricing,
    )


class IndividualLicenseTypeInfo(BaseModel):
    """Info about an individual license type extracted from combined license strings."""

    license_type: str
    display_name: str | None = None
    user_count: int  # Number of users with this license
    pricing: LicenseTypePricing | None = None


class IndividualLicenseTypesResponse(BaseModel):
    """Response with individual license types extracted from combined strings."""

    license_types: list[IndividualLicenseTypeInfo]
    has_combined_types: bool  # True if any license_type contains commas


class IndividualLicenseTypePricingRequest(BaseModel):
    """Request to update individual license type pricing."""

    pricing: list[LicenseTypePricing]


@router.get("/{provider_id}/individual-license-types", response_model=IndividualLicenseTypesResponse)
async def get_provider_individual_license_types(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> IndividualLicenseTypesResponse:
    """Get individual license types extracted from combined strings.

    For providers like Microsoft 365 where users have multiple licenses stored as
    comma-separated strings (e.g., "E5, Power BI, Teams"), this extracts and counts
    each individual license type separately.

    Requires providers.view permission.
    """
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Get individual license type counts (extracted from combined strings)
    individual_counts, has_combined = await provider_service.get_individual_license_type_counts(provider_id)

    # Get current individual pricing from config
    individual_pricing_config = (provider.config or {}).get("individual_license_pricing", {})

    license_types = []
    for license_type, count in individual_counts.items():
        price_info = individual_pricing_config.get(license_type)
        pricing = None
        if price_info:
            pricing = LicenseTypePricing(
                license_type=license_type,
                display_name=price_info.get("display_name"),
                cost=price_info.get("cost", "0"),
                currency=price_info.get("currency", "EUR"),
                billing_cycle=price_info.get("billing_cycle", "monthly"),
                payment_frequency=price_info.get("payment_frequency", "monthly"),
                next_billing_date=price_info.get("next_billing_date"),
                notes=price_info.get("notes"),
            )
        license_types.append(
            IndividualLicenseTypeInfo(
                license_type=license_type,
                display_name=price_info.get("display_name") if price_info else None,
                user_count=count,
                pricing=pricing,
            )
        )

    # Sort by user count descending
    license_types.sort(key=lambda x: x.user_count, reverse=True)

    return IndividualLicenseTypesResponse(
        license_types=license_types,
        has_combined_types=has_combined,
    )


@router.put("/{provider_id}/individual-pricing", response_model=IndividualLicenseTypesResponse)
async def update_provider_individual_pricing(
    http_request: Request,
    provider_id: UUID,
    request: IndividualLicenseTypePricingRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_repo: Annotated[ProviderRepository, Depends(get_provider_repository)],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> IndividualLicenseTypesResponse:
    """Update individual license type pricing.

    For combined license types, the total monthly cost is calculated as the sum of
    individual license prices. For example, if a user has "E5, Power BI, Teams":
    - E5 = 30 EUR/month
    - Power BI = 10 EUR/month
    - Teams = 0 EUR/month (free)
    - Total = 40 EUR/month

    Requires providers.edit permission.
    """
    provider = await provider_repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Build individual pricing config
    individual_pricing_config = {}
    for p in request.pricing:
        individual_pricing_config[p.license_type] = {
            "cost": p.cost,
            "currency": p.currency,
            "billing_cycle": p.billing_cycle,
            "payment_frequency": p.payment_frequency,
            "display_name": p.display_name,
            "next_billing_date": p.next_billing_date,
            "notes": p.notes,
        }

    # Use pricing service to update (handles audit logging and commit)
    await pricing_service.update_individual_license_pricing(
        provider_id=provider_id,
        individual_pricing_config=individual_pricing_config,
        user=current_user,
        request=http_request,
    )

    # Return updated license types
    return await get_provider_individual_license_types(provider_id, current_user, provider_repo, provider_service)


@router.post("/sync/avatars", response_model=SyncResponse)
async def resync_avatars(
    http_request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    audit_service: Annotated[AuditService, Depends(get_audit_service)],
    force: bool = False,
) -> SyncResponse:
    """Resync all employee avatars from HiBob.

    Args:
        force: If True, delete existing avatars and re-download all.
               If False (default), only download missing avatars.

    Requires providers.sync permission.
    """
    try:
        results = await sync_service.resync_avatars(force=force)

        # Audit log
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=None,
            user=current_user,
            request=http_request,
            details={"action": "avatar_resync", "force": force, "results": results},
        )

        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HiBob provider not configured",
        )
    except (ConnectionError, TimeoutError, OSError) as e:
        # Network/connection errors - audit and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=None,
            user=current_user,
            request=http_request,
            details={"action": "avatar_resync", "success": False, "error_code": "CONNECTION_ERROR", "error_type": type(e).__name__},
        )
        return SyncResponse(success=False, results={"error": "Connection to HiBob failed"})
    except Exception as e:
        # Unexpected errors - audit with sanitized details and return failure
        await audit_service.log(
            action=AuditAction.PROVIDER_SYNC,
            resource_type=ResourceType.PROVIDER,
            resource_id=None,
            user=current_user,
            request=http_request,
            details={"action": "avatar_resync", "success": False, **sanitize_error_for_audit(e)},
        )
        return SyncResponse(success=False, results={"error": "Avatar sync failed"})
