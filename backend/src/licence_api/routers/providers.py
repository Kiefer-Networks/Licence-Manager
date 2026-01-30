"""Providers router."""

import copy
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

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
from licence_api.routers.payment_methods import calculate_expiry_info
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.security.auth import get_current_user, require_permission, Permissions
from licence_api.security.encryption import get_encryption_service
from licence_api.security.rate_limit import limiter
from licence_api.services.sync_service import SyncService

router = APIRouter()

# Rate limit for credential testing to prevent brute force
TEST_CONNECTION_LIMIT = "10/minute"


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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderListResponse:
    """List all configured providers. Requires providers.view permission."""
    from licence_api.models.dto.provider import ProviderLicenseStats
    from licence_api.repositories.license_repository import LicenseRepository
    from licence_api.repositories.settings_repository import SettingsRepository

    repo = ProviderRepository(db)
    license_repo = LicenseRepository(db)
    settings_repo = SettingsRepository(db)

    providers_with_counts = await repo.get_all_with_license_counts()

    # Get company domains for external detection
    domains_setting = await settings_repo.get("company_domains")
    company_domains = [d.lower() for d in (domains_setting.get("domains") or [])] if domains_setting else []

    # Get license stats per provider
    license_stats = await license_repo.get_stats_by_provider(company_domains)

    items = []
    for p, count in providers_with_counts:
        pm_summary = None
        if p.payment_method:
            is_expiring, _ = calculate_expiry_info(p.payment_method)
            pm_summary = PaymentMethodSummary(
                id=p.payment_method.id,
                name=p.payment_method.name,
                type=p.payment_method.type,
                is_expiring=is_expiring,
            )

        # Get stats for this provider
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

    return ProviderListResponse(items=items, total=len(items))


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_VIEW))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderResponse:
    """Get a single provider by ID. Requires providers.view permission."""
    repo = ProviderRepository(db)
    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    from licence_api.repositories.license_repository import LicenseRepository
    license_repo = LicenseRepository(db)
    counts = await license_repo.count_by_provider()
    license_count = counts.get(provider_id, 0)

    pm_summary = None
    if provider.payment_method:
        is_expiring, _ = calculate_expiry_info(provider.payment_method)
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


@router.post("", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    request: ProviderCreate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_CREATE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderResponse:
    """Create a new provider. Requires providers.create permission."""
    repo = ProviderRepository(db)

    # Check if provider already exists
    existing = await repo.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Provider {request.name} already configured",
        )

    # Encrypt credentials
    encryption = get_encryption_service()
    encrypted_creds = encryption.encrypt(request.credentials)

    provider = await repo.create(
        name=request.name,
        display_name=request.display_name,
        credentials_encrypted=encrypted_creds,
        config=request.config or {},
    )

    return ProviderResponse(
        id=provider.id,
        name=provider.name,
        display_name=provider.display_name,
        enabled=provider.enabled,
        config=provider.config,
        last_sync_at=provider.last_sync_at,
        last_sync_status=provider.last_sync_status,
        license_count=0,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: UUID,
    request: ProviderUpdate,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProviderResponse:
    """Update a provider. Requires providers.edit permission."""
    repo = ProviderRepository(db)
    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    update_data: dict[str, Any] = {}

    if request.display_name is not None:
        update_data["display_name"] = request.display_name

    if request.enabled is not None:
        update_data["enabled"] = request.enabled

    if request.config is not None:
        update_data["config"] = request.config

    if request.credentials is not None:
        encryption = get_encryption_service()
        update_data["credentials_encrypted"] = encryption.encrypt(request.credentials)

    if request.payment_method_id is not None:
        update_data["payment_method_id"] = request.payment_method_id

    if update_data:
        provider = await repo.update(provider_id, **update_data)

    from licence_api.repositories.license_repository import LicenseRepository
    license_repo = LicenseRepository(db)
    counts = await license_repo.count_by_provider()

    # Refresh to get payment method relationship
    await db.refresh(provider)

    pm_summary = None
    if provider.payment_method:
        is_expiring, _ = calculate_expiry_info(provider.payment_method)
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


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_DELETE))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a provider. Requires providers.delete permission."""
    repo = ProviderRepository(db)
    deleted = await repo.delete(provider_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )


@router.post("/test-connection", response_model=TestConnectionResponse)
@limiter.limit(TEST_CONNECTION_LIMIT)
async def test_provider_connection(
    http_request: Request,
    request: TestConnectionRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_CREATE))],
) -> TestConnectionResponse:
    """Test provider connection with given credentials. Requires providers.create permission."""
    # Manual providers don't need connection test
    if request.name == "manual":
        return TestConnectionResponse(
            success=True,
            message="Manual provider - no connection test needed",
        )

    from licence_api.providers import (
        HiBobProvider,
        GoogleWorkspaceProvider,
        MicrosoftProvider,
        OpenAIProvider,
        FigmaProvider,
        CursorProvider,
        SlackProvider,
        JetBrainsProvider,
    )

    providers = {
        ProviderName.HIBOB: HiBobProvider,
        ProviderName.GOOGLE_WORKSPACE: GoogleWorkspaceProvider,
        ProviderName.MICROSOFT: MicrosoftProvider,
        ProviderName.OPENAI: OpenAIProvider,
        ProviderName.FIGMA: FigmaProvider,
        ProviderName.CURSOR: CursorProvider,
        ProviderName.SLACK: SlackProvider,
        ProviderName.JETBRAINS: JetBrainsProvider,
    }

    provider_class = providers.get(ProviderName(request.name) if request.name in [e.value for e in ProviderName] else None)
    if provider_class is None:
        return TestConnectionResponse(
            success=False,
            message=f"Unknown provider: {request.name}",
        )

    try:
        provider = provider_class(request.credentials)
        success = await provider.test_connection()
        return TestConnectionResponse(
            success=success,
            message="Connection successful" if success else "Connection failed",
        )
    except Exception:
        return TestConnectionResponse(
            success=False,
            message="Connection failed. Please verify your credentials.",
        )


@router.post("/sync", response_model=SyncResponse)
async def trigger_sync(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    db: Annotated[AsyncSession, Depends(get_db)],
    provider_id: UUID | None = None,
) -> SyncResponse:
    """Trigger a sync operation. Requires providers.sync permission."""
    service = SyncService(db)
    try:
        results = await service.trigger_sync(provider_id)
        return SyncResponse(success=True, results=results)
    except Exception:
        return SyncResponse(success=False, results={"error": "Sync operation failed"})


@router.post("/{provider_id}/sync", response_model=SyncResponse)
async def sync_provider(
    provider_id: UUID,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResponse:
    """Sync a specific provider. Requires providers.sync permission."""
    service = SyncService(db)
    try:
        results = await service.sync_provider(provider_id)
        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )
    except Exception:
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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseTypesResponse:
    """Get all license types for a provider with their counts and current pricing. Requires providers.view permission."""
    from licence_api.repositories.license_repository import LicenseRepository

    repo = ProviderRepository(db)
    license_repo = LicenseRepository(db)

    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Get license type counts
    type_counts = await license_repo.get_license_type_counts(provider_id)

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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseTypePricingResponse:
    """Get license type pricing for a provider. Requires providers.view permission."""
    repo = ProviderRepository(db)
    provider = await repo.get_by_id(provider_id)
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
    provider_id: UUID,
    request: LicenseTypePricingRequest,
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_EDIT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LicenseTypePricingResponse:
    """Update license type pricing for a provider. Requires providers.edit permission."""
    from licence_api.repositories.license_repository import LicenseRepository
    from decimal import Decimal

    repo = ProviderRepository(db)
    license_repo = LicenseRepository(db)

    provider = await repo.get_by_id(provider_id)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    # Create a copy of config to ensure SQLAlchemy detects the change
    config = copy.deepcopy(provider.config) if provider.config else {}

    # Handle package pricing (for providers like Mattermost with bulk licenses)
    if request.package_pricing and request.package_pricing.cost:
        package_config = {
            "cost": request.package_pricing.cost,
            "currency": request.package_pricing.currency,
            "billing_cycle": request.package_pricing.billing_cycle,
            "next_billing_date": request.package_pricing.next_billing_date,
            "notes": request.package_pricing.notes,
        }
        config["package_pricing"] = package_config

        # Calculate monthly package cost
        package_cost = Decimal(request.package_pricing.cost)
        if request.package_pricing.billing_cycle == "yearly":
            monthly_package_cost = package_cost / 12
        else:
            monthly_package_cost = package_cost

        # Get package size (max_users) from provider_license_info
        license_info = config.get("provider_license_info", {})
        max_users = license_info.get("max_users", 0)

        if max_users > 0:
            # Calculate cost per user based on package size (not active users)
            # Example: 52250 EUR/year / 500 users = 104.50 EUR/year per user = 8.71 EUR/month per user
            cost_per_license = monthly_package_cost / max_users
            await license_repo.update_all_active_pricing(
                provider_id=provider_id,
                monthly_cost=cost_per_license,
                currency=request.package_pricing.currency,
            )
    else:
        # Clear package pricing if not provided
        config.pop("package_pricing", None)

    # Build individual license type pricing config
    pricing_config = {}
    for p in request.pricing:
        if p.cost and p.cost != "0":
            pricing_config[p.license_type] = {
                "cost": p.cost,
                "currency": p.currency,
                "billing_cycle": p.billing_cycle,
                "payment_frequency": p.payment_frequency,
                "display_name": p.display_name,
                "next_billing_date": p.next_billing_date,
                "notes": p.notes,
            }

    config["license_pricing"] = pricing_config
    await repo.update(provider_id, config=config)

    # Apply individual license type pricing (overrides package pricing for specific types)
    for p in request.pricing:
        if p.cost:
            # Calculate monthly equivalent cost
            cost = Decimal(p.cost)
            if p.billing_cycle == "yearly":
                monthly_cost = cost / 12
            elif p.billing_cycle == "monthly":
                monthly_cost = cost
            else:
                # perpetual/one_time - no recurring monthly cost
                monthly_cost = Decimal("0")

            await license_repo.update_pricing_by_type(
                provider_id=provider_id,
                license_type=p.license_type,
                monthly_cost=monthly_cost,
                currency=p.currency,
            )

    await db.commit()

    return LicenseTypePricingResponse(
        pricing=request.pricing,
        package_pricing=request.package_pricing,
    )


@router.post("/sync/avatars", response_model=SyncResponse)
async def resync_avatars(
    current_user: Annotated[AdminUser, Depends(require_permission(Permissions.PROVIDERS_SYNC))],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = False,
) -> SyncResponse:
    """Resync all employee avatars from HiBob.

    Args:
        force: If True, delete existing avatars and re-download all.
               If False (default), only download missing avatars.

    Requires providers.sync permission.
    """
    service = SyncService(db)
    try:
        results = await service.resync_avatars(force=force)
        return SyncResponse(success=True, results=results)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="HiBob provider not configured",
        )
    except Exception:
        return SyncResponse(success=False, results={"error": "Avatar sync failed"})
