"""Providers router."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Path, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from licence_api.dependencies import (
    get_pricing_service,
    get_provider_service,
    get_sync_service,
)
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.provider import (
    IndividualLicenseTypeInfo,
    LicenseTypeInfo,
    LicenseTypePricing,
    PackagePricing,
    ProviderCreate,
    ProviderListResponse,
    ProviderResponse,
    ProviderUpdate,
)
from licence_api.security.auth import Permissions, require_permission
from licence_api.security.rate_limit import (
    API_DEFAULT_LIMIT,
    EXPENSIVE_READ_LIMIT,
    PROVIDER_TEST_CONNECTION_LIMIT,
    SENSITIVE_OPERATION_LIMIT,
    limiter,
)
from licence_api.services.pricing_service import PricingService
from licence_api.services.provider_service import ProviderService
from licence_api.services.sync_service import SyncService
from licence_api.utils.validation import validate_dict_recursive

router = APIRouter()


class TestConnectionRequest(BaseModel):
    """Request to test provider connection."""

    name: str = Field(max_length=100)  # Provider name
    credentials: dict[str, Any]

    @field_validator("credentials")
    @classmethod
    def validate_credentials_size(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate credentials dict size and content recursively."""
        validate_dict_recursive(v, max_depth=3, current_depth=0)
        return v


class PublicCredentialsResponse(BaseModel):
    """Response with non-secret credential values."""

    credentials: dict[str, str]


class TestConnectionResponse(BaseModel):
    """Response from connection test."""

    success: bool
    message: str


class SyncResponse(BaseModel):
    """Response from sync operation."""

    success: bool
    results: dict[str, Any]


@router.get("", response_model=ProviderListResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def list_providers(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderListResponse:
    """List all configured providers. Requires providers.view permission.

    Response is cached for 5 minutes to improve performance.
    """
    items = await provider_service.list_providers_cached()
    return ProviderListResponse(items=items, total=len(items))


@router.get("/{provider_id}", response_model=ProviderResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_provider(
    request: Request,
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


@router.get("/{provider_id}/public-credentials", response_model=PublicCredentialsResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_provider_public_credentials(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> PublicCredentialsResponse:
    """Get non-secret credential values for a provider.

    Returns values like base_url, org_id, domain etc. that are not secrets.
    Secret fields (tokens, keys, passwords) are excluded.

    Requires providers.view permission.
    """
    try:
        public_credentials = await provider_service.get_public_credentials(provider_id)
        return PublicCredentialsResponse(credentials=public_credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def create_provider(
    request: Request,
    body: ProviderCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_CREATE))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Create a new provider. Requires providers.create permission."""
    try:
        return await provider_service.create_provider(
            name=body.name,
            display_name=body.display_name,
            credentials=body.credentials,
            config=body.config,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider with this name already exists or configuration is invalid",
        )


@router.put("/{provider_id}", response_model=ProviderResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_provider(
    request: Request,
    provider_id: UUID,
    body: ProviderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> ProviderResponse:
    """Update a provider. Requires providers.edit permission."""
    result = await provider_service.update_provider(
        provider_id=provider_id,
        display_name=body.display_name,
        logo_url=body.logo_url,
        enabled=body.enabled,
        config=body.config,
        credentials=body.credentials,
        payment_method_id=body.payment_method_id,
        user=current_user,
        request=request,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    return result


# Maximum logo file size: 5MB
MAX_LOGO_SIZE = 5 * 1024 * 1024


class LogoUploadResponse(BaseModel):
    """Logo upload response."""

    logo_url: str


@router.post("/{provider_id}/logo", response_model=LogoUploadResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def upload_provider_logo(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
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

    content = await file.read(MAX_LOGO_SIZE + 1)
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logo file too large. Maximum size: {MAX_LOGO_SIZE // 1024 // 1024}MB",
        )

    try:
        logo_url = await provider_service.upload_logo(
            provider_id=provider_id,
            content=content,
            filename=file.filename,
            user=current_user,
            request=request,
        )
        return LogoUploadResponse(logo_url=logo_url)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid logo file",
        )


@router.get("/{provider_id}/logo/{filename}")
@limiter.limit(API_DEFAULT_LIMIT)
async def get_provider_logo_file(
    request: Request,
    provider_id: UUID,
    filename: Annotated[str, Path(max_length=100, pattern=r"^[a-zA-Z0-9_.-]+$")],
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> FileResponse:
    """Get a provider's logo file.

    Validates that the requested logo belongs to the provider and serves the file.
    Requires providers.view permission.
    """
    try:
        file_path, media_type = await provider_service.get_logo_file_path(
            provider_id, filename
        )
        return FileResponse(path=file_path, media_type=media_type)
    except ValueError as e:
        error_msg = str(e)
        if error_msg == "Provider not found" or error_msg == "Logo not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        elif error_msg == "Access denied":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename",
            )


@router.delete("/{provider_id}/logo", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_provider_logo(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_DELETE))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> None:
    """Delete a provider's logo. Requires providers.delete permission."""
    try:
        await provider_service.delete_logo(
            provider_id=provider_id,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider or logo not found",
        )


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def delete_provider(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_DELETE))],
    provider_service: Annotated[ProviderService, Depends(get_provider_service)],
) -> None:
    """Delete a provider. Requires providers.delete permission."""
    deleted = await provider_service.delete_provider(
        provider_id=provider_id,
        user=current_user,
        request=request,
    )
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )


@router.post("/test-connection", response_model=TestConnectionResponse)
@limiter.limit(PROVIDER_TEST_CONNECTION_LIMIT)
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
    success, message = await ProviderService.test_connection(body.name, body.credentials)
    return TestConnectionResponse(success=success, message=message)


@router.post("/sync", response_model=SyncResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def trigger_sync(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    provider_id: UUID | None = None,
) -> SyncResponse:
    """Trigger a sync operation. Requires providers.sync permission."""
    try:
        results = await sync_service.trigger_sync(
            provider_id=provider_id,
            user=current_user,
            request=request,
        )
        return SyncResponse(success=True, results=results)
    except (ConnectionError, TimeoutError, OSError):
        return SyncResponse(success=False, results={"error": "Connection to provider failed"})
    except ValueError:
        return SyncResponse(success=False, results={"error": "Invalid provider configuration"})
    except Exception:
        return SyncResponse(success=False, results={"error": "Sync operation failed"})


@router.post("/{provider_id}/sync", response_model=SyncResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def sync_provider(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
) -> SyncResponse:
    """Sync a specific provider. Requires providers.sync permission."""
    try:
        results = await sync_service.trigger_provider_sync(
            provider_id=provider_id,
            user=current_user,
            request=request,
        )
        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    except (ConnectionError, TimeoutError, OSError):
        return SyncResponse(success=False, results={"error": "Connection to provider failed"})
    except Exception:
        return SyncResponse(success=False, results={"error": "Sync operation failed"})


class LicenseTypePricingResponse(BaseModel):
    """Response with all license type pricing."""

    pricing: list[LicenseTypePricing]
    package_pricing: PackagePricing | None = None


class LicenseTypePricingRequest(BaseModel):
    """Request to update license type pricing."""

    pricing: list[LicenseTypePricing] = Field(max_length=500)
    package_pricing: PackagePricing | None = None


class LicenseTypesResponse(BaseModel):
    """Response with all license types for a provider."""

    license_types: list[LicenseTypeInfo]


@router.get("/{provider_id}/license-types", response_model=LicenseTypesResponse)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_provider_license_types(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> LicenseTypesResponse:
    """Get all license types for a provider with their counts and current pricing.

    Requires providers.view permission.
    """
    try:
        license_types = await pricing_service.get_license_type_overview(provider_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return LicenseTypesResponse(license_types=license_types)


@router.get("/{provider_id}/pricing", response_model=LicenseTypePricingResponse)
@limiter.limit(API_DEFAULT_LIMIT)
async def get_provider_pricing(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> LicenseTypePricingResponse:
    """Get license type pricing for a provider. Requires providers.view permission."""
    try:
        pricing, package_pricing = await pricing_service.get_pricing_overview(provider_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return LicenseTypePricingResponse(pricing=pricing, package_pricing=package_pricing)


@router.put("/{provider_id}/pricing", response_model=LicenseTypePricingResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_provider_pricing(
    request: Request,
    provider_id: UUID,
    body: LicenseTypePricingRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> LicenseTypePricingResponse:
    """Update license type pricing for a provider. Requires providers.edit permission."""
    try:
        await pricing_service.update_license_pricing(
            provider_id=provider_id,
            pricing=body.pricing,
            package_pricing=body.package_pricing,
            user=current_user,
            request=request,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return LicenseTypePricingResponse(
        pricing=body.pricing,
        package_pricing=body.package_pricing,
    )


class IndividualLicenseTypesResponse(BaseModel):
    """Response with individual license types extracted from combined strings."""

    license_types: list[IndividualLicenseTypeInfo]
    has_combined_types: bool  # True if any license_type contains commas


class IndividualLicenseTypePricingRequest(BaseModel):
    """Request to update individual license type pricing."""

    pricing: list[LicenseTypePricing] = Field(max_length=500)


@router.get(
    "/{provider_id}/individual-license-types", response_model=IndividualLicenseTypesResponse
)
@limiter.limit(EXPENSIVE_READ_LIMIT)
async def get_provider_individual_license_types(
    request: Request,
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    pricing_service: Annotated[PricingService, Depends(get_pricing_service)],
) -> IndividualLicenseTypesResponse:
    """Get individual license types extracted from combined strings.

    For providers like Microsoft 365 where users have multiple licenses stored as
    comma-separated strings (e.g., "E5, Power BI, Teams"), this extracts and counts
    each individual license type separately.

    Requires providers.view permission.
    """
    try:
        license_types, has_combined_types = (
            await pricing_service.get_individual_license_type_overview(provider_id)
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return IndividualLicenseTypesResponse(
        license_types=license_types,
        has_combined_types=has_combined_types,
    )


@router.put("/{provider_id}/individual-pricing", response_model=IndividualLicenseTypesResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def update_provider_individual_pricing(
    request: Request,
    provider_id: UUID,
    body: IndividualLicenseTypePricingRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
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
    try:
        license_types, has_combined_types = (
            await pricing_service.update_individual_license_pricing(
                provider_id=provider_id,
                pricing=body.pricing,
                user=current_user,
                request=request,
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return IndividualLicenseTypesResponse(
        license_types=license_types,
        has_combined_types=has_combined_types,
    )


@router.post("/sync/avatars", response_model=SyncResponse)
@limiter.limit(SENSITIVE_OPERATION_LIMIT)
async def resync_avatars(
    request: Request,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    sync_service: Annotated[SyncService, Depends(get_sync_service)],
    force: bool = False,
) -> SyncResponse:
    """Resync all employee avatars from HiBob.

    Args:
        force: If True, delete existing avatars and re-download all.
               If False (default), only download missing avatars.

    Requires providers.sync permission.
    """
    try:
        results = await sync_service.resync_avatars(
            force=force,
            user=current_user,
            request=request,
        )
        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HiBob provider not configured",
        )
    except (ConnectionError, TimeoutError, OSError):
        return SyncResponse(success=False, results={"error": "Connection to HiBob failed"})
    except Exception:
        return SyncResponse(success=False, results={"error": "Avatar sync failed"})
