"""Pricing service for managing provider license costs."""

import copy
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.dto.provider import (
    IndividualLicenseTypeInfo,
    LicenseTypeInfo,
    LicenseTypePricing,
    PackagePricing,
)
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

if TYPE_CHECKING:
    from licence_api.models.domain.admin_user import AdminUser

# Default license types for providers where types are known but may not be auto-detected
PROVIDER_DEFAULT_LICENSE_TYPES: dict[str, list[str]] = {
    "figma": [
        "Figma Viewer",
        "Figma Collaborator",
        "Figma Dev Mode",
        "Figma Full Seat",
    ],
}


class PricingService:
    """Service for managing license pricing calculations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.provider_repo = ProviderRepository(session)
        self.license_repo = LicenseRepository(session)
        self.audit_service = AuditService(session)

    async def update_license_pricing(
        self,
        provider_id: UUID,
        pricing: list[LicenseTypePricing],
        package_pricing: PackagePricing | None = None,
        user: "AdminUser | None" = None,
        request: Request | None = None,
    ) -> None:
        """Update license pricing for a provider.

        Accepts raw pricing DTOs, converts them to config dicts internally,
        and applies pricing updates to the database.

        Args:
            provider_id: Provider UUID
            pricing: List of license type pricing DTOs
            package_pricing: Optional package pricing DTO for bulk licenses
            user: Admin user making the change
            request: HTTP request for audit logging
        """
        # Convert DTOs to config dicts
        pricing_config = self._build_pricing_config_dict(pricing)
        package_pricing_dict = self._build_package_pricing_dict(package_pricing)

        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Create a copy of config to ensure SQLAlchemy detects the change
        config = copy.deepcopy(provider.config) if provider.config else {}

        # Handle package pricing (for providers like Mattermost with bulk licenses)
        if package_pricing_dict and package_pricing_dict.get("cost"):
            config["package_pricing"] = package_pricing_dict

            # Calculate monthly package cost
            package_cost = Decimal(package_pricing_dict["cost"])
            billing_cycle = package_pricing_dict.get("billing_cycle", "yearly")
            if billing_cycle == "yearly":
                monthly_package_cost = package_cost / 12
            elif billing_cycle == "quarterly":
                monthly_package_cost = package_cost / 3
            else:
                monthly_package_cost = package_cost

            # Get package size (max_users) from provider_license_info
            license_info = config.get("provider_license_info", {})
            max_users = license_info.get("max_users", 0)

            if max_users > 0:
                # Calculate cost per user based on package size
                cost_per_license = monthly_package_cost / max_users
                await self.license_repo.update_all_active_pricing(
                    provider_id=provider_id,
                    monthly_cost=cost_per_license,
                    currency=package_pricing_dict.get("currency", "EUR"),
                )
        else:
            # Clear package pricing if not provided
            config.pop("package_pricing", None)

        # Build individual license type pricing config
        config["license_pricing"] = pricing_config
        await self.provider_repo.update(provider_id, config=config)

        # Apply individual license type pricing (overrides package pricing for specific types)
        for license_type, price_info in pricing_config.items():
            cost_str = price_info.get("cost")
            if cost_str:
                cost = Decimal(cost_str)
                billing_cycle = price_info.get("billing_cycle", "yearly")
                if billing_cycle == "yearly":
                    monthly_cost = cost / 12
                elif billing_cycle == "quarterly":
                    monthly_cost = cost / 3
                elif billing_cycle == "monthly":
                    monthly_cost = cost
                else:
                    # perpetual/one_time - no recurring monthly cost
                    monthly_cost = Decimal("0")

                await self.license_repo.update_pricing_by_type(
                    provider_id=provider_id,
                    license_type=license_type,
                    monthly_cost=monthly_cost,
                    currency=price_info.get("currency", "EUR"),
                )

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={
                    "action": "pricing_update",
                    "license_types_count": len(pricing_config),
                    "has_package_pricing": package_pricing is not None,
                },
            )

        await self.session.commit()

    async def update_individual_license_pricing(
        self,
        provider_id: UUID,
        pricing: list[LicenseTypePricing],
        user: "AdminUser | None" = None,
        request: Request | None = None,
    ) -> tuple[list[IndividualLicenseTypeInfo], bool]:
        """Update individual license type pricing (for combined license types).

        Accepts raw pricing DTOs, converts them to config dicts internally,
        applies pricing updates, and returns the updated overview.

        For combined license types, the total monthly cost is calculated as the sum of
        individual license prices. For example, if a user has "E5, Power BI, Teams":
        - E5 = 30 EUR/month
        - Power BI = 10 EUR/month
        - Teams = 0 EUR/month (free)
        - Total = 40 EUR/month

        Args:
            provider_id: Provider UUID
            pricing: List of individual license type pricing DTOs
            user: Admin user making the change
            request: HTTP request for audit logging

        Returns:
            Tuple of (list of IndividualLicenseTypeInfo, has_combined_types flag)
        """
        # Convert DTOs to config dict
        individual_pricing_config = self._build_individual_pricing_config_dict(pricing)

        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Create a copy of config
        config = copy.deepcopy(provider.config) if provider.config else {}

        # Build individual pricing dict for license updates
        individual_pricing_dict: dict[str, tuple[Decimal | None, str]] = {}

        for license_type, price_info in individual_pricing_config.items():
            cost_str = price_info.get("cost")
            if cost_str:
                cost = Decimal(cost_str)
                billing_cycle = price_info.get("billing_cycle", "monthly")
                if billing_cycle == "yearly":
                    monthly_cost = cost / 12
                elif billing_cycle == "quarterly":
                    monthly_cost = cost / 3
                elif billing_cycle == "monthly":
                    monthly_cost = cost
                else:
                    monthly_cost = Decimal("0")
                individual_pricing_dict[license_type] = (
                    monthly_cost,
                    price_info.get("currency", "EUR"),
                )

        config["individual_license_pricing"] = individual_pricing_config
        await self.provider_repo.update(provider_id, config=config)

        # Apply individual pricing to all licenses (sum of individual prices)
        await self.license_repo.update_pricing_by_individual_type(
            provider_id=provider_id,
            individual_pricing=individual_pricing_dict,
        )

        # Audit log
        if user:
            await self.audit_service.log(
                action=AuditAction.PROVIDER_UPDATE,
                resource_type=ResourceType.PROVIDER,
                resource_id=provider_id,
                user=user,
                request=request,
                details={
                    "action": "individual_pricing_update",
                    "license_types_count": len(individual_pricing_config),
                },
            )

        await self.session.commit()

        # Return updated overview
        return await self.get_individual_license_type_overview(provider_id)

    # =========================================================================
    # Read / Overview methods
    # =========================================================================

    async def get_license_type_overview(
        self, provider_id: UUID
    ) -> list[LicenseTypeInfo]:
        """Get all license types for a provider with counts and current pricing.

        Merges license type counts with pricing configuration and default types.

        Args:
            provider_id: Provider UUID

        Returns:
            List of LicenseTypeInfo DTOs sorted by count descending

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        provider_name = provider.name
        config = provider.config or {}

        # Get license type counts
        type_counts = await self.license_repo.get_license_type_counts(provider_id)

        # Get current pricing from config
        pricing_config = config.get("license_pricing", {})

        # Add default license types for providers with known types (e.g., Figma)
        default_types = PROVIDER_DEFAULT_LICENSE_TYPES.get(provider_name, [])
        for default_type in default_types:
            if default_type not in type_counts:
                type_counts[default_type] = 0

        license_types: list[LicenseTypeInfo] = []
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
                    purchased_quantity=price_info.get("purchased_quantity"),
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

        return license_types

    async def get_pricing_overview(
        self, provider_id: UUID
    ) -> tuple[list[LicenseTypePricing], PackagePricing | None]:
        """Get license type pricing for a provider.

        Assembles pricing data from provider config into a structured response.

        Args:
            provider_id: Provider UUID

        Returns:
            Tuple of (list of LicenseTypePricing DTOs, optional PackagePricing DTO)

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        config = provider.config or {}
        pricing_config = config.get("license_pricing", {})

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
                purchased_quantity=info.get("purchased_quantity"),
            )
            for lt, info in pricing_config.items()
        ]

        # Get package pricing if exists
        package_pricing_config = config.get("package_pricing")
        package_pricing = None
        if package_pricing_config:
            package_pricing = PackagePricing(
                cost=package_pricing_config.get("cost", "0"),
                currency=package_pricing_config.get("currency", "EUR"),
                billing_cycle=package_pricing_config.get("billing_cycle", "yearly"),
                next_billing_date=package_pricing_config.get("next_billing_date"),
                notes=package_pricing_config.get("notes"),
            )

        return pricing, package_pricing

    async def get_individual_license_type_overview(
        self, provider_id: UUID
    ) -> tuple[list[IndividualLicenseTypeInfo], bool]:
        """Get individual license types extracted from combined strings with pricing.

        For providers like Microsoft 365 where users have multiple licenses stored as
        comma-separated strings, this extracts and counts each individual license type
        separately.

        Args:
            provider_id: Provider UUID

        Returns:
            Tuple of (list of IndividualLicenseTypeInfo DTOs, has_combined_types flag)

        Raises:
            ValueError: If provider not found
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        config = provider.config or {}

        # Get individual license type counts (extracted from combined strings)
        individual_counts = await self.license_repo.get_individual_license_type_counts(
            provider_id
        )
        raw_counts = await self.license_repo.get_license_type_counts(provider_id)
        has_combined = any("," in lt for lt in raw_counts.keys())

        # Get current individual pricing from config
        individual_pricing_config = config.get("individual_license_pricing", {})

        license_types: list[IndividualLicenseTypeInfo] = []
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
                    purchased_quantity=price_info.get("purchased_quantity"),
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

        return license_types, has_combined

    @staticmethod
    def calculate_monthly_cost(cost: Decimal, billing_cycle: str) -> Decimal:
        """Calculate monthly cost from billing cycle.

        Args:
            cost: Raw cost amount
            billing_cycle: Billing cycle (yearly, quarterly, monthly, perpetual, one_time)

        Returns:
            Monthly equivalent cost
        """
        if billing_cycle == "yearly":
            return cost / 12
        elif billing_cycle == "quarterly":
            return cost / 3
        elif billing_cycle == "monthly":
            return cost
        else:
            # perpetual/one_time - no recurring monthly cost
            return Decimal("0")

    @staticmethod
    def _build_package_pricing_dict(package_pricing: PackagePricing | None) -> dict | None:
        """Build package pricing dictionary from a PackagePricing DTO.

        Args:
            package_pricing: PackagePricing DTO

        Returns:
            Dict with package pricing info, or None if no valid cost provided
        """
        if package_pricing and package_pricing.cost:
            return {
                "cost": package_pricing.cost,
                "currency": package_pricing.currency,
                "billing_cycle": package_pricing.billing_cycle,
                "next_billing_date": package_pricing.next_billing_date,
                "notes": package_pricing.notes,
            }
        return None

    @staticmethod
    def _build_individual_pricing_config_dict(pricing_list: list[LicenseTypePricing]) -> dict:
        """Build individual pricing config dictionary from a list of pricing DTOs.

        Args:
            pricing_list: List of LicenseTypePricing DTOs

        Returns:
            Dict mapping license_type to pricing info
        """
        individual_pricing_config = {}
        for p in pricing_list:
            individual_pricing_config[p.license_type] = {
                "cost": p.cost,
                "currency": p.currency,
                "billing_cycle": p.billing_cycle,
                "payment_frequency": p.payment_frequency,
                "display_name": p.display_name,
                "next_billing_date": p.next_billing_date,
                "notes": p.notes,
                "purchased_quantity": p.purchased_quantity,
            }
        return individual_pricing_config

    @staticmethod
    def _build_pricing_config_dict(pricing_list: list[LicenseTypePricing]) -> dict:
        """Build pricing config dictionary from a list of pricing DTOs.

        Args:
            pricing_list: List of LicenseTypePricing DTOs

        Returns:
            Dict mapping license_type to pricing info
        """
        pricing_config = {}
        for p in pricing_list:
            if p.cost and p.cost != "0":
                pricing_config[p.license_type] = {
                    "cost": p.cost,
                    "currency": p.currency,
                    "billing_cycle": p.billing_cycle,
                    "payment_frequency": p.payment_frequency,
                    "display_name": p.display_name,
                    "next_billing_date": p.next_billing_date,
                    "notes": p.notes,
                    "purchased_quantity": p.purchased_quantity,
                }
        return pricing_config
