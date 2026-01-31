"""Pricing service for managing provider license costs."""

import copy
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository


class PricingService:
    """Service for managing license pricing calculations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.provider_repo = ProviderRepository(session)
        self.license_repo = LicenseRepository(session)

    async def update_license_pricing(
        self,
        provider_id: UUID,
        pricing_config: dict,
        package_pricing: dict | None = None,
    ) -> None:
        """Update license pricing for a provider.

        Args:
            provider_id: Provider UUID
            pricing_config: Dict of license_type -> pricing info
            package_pricing: Optional package pricing for bulk licenses
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Create a copy of config to ensure SQLAlchemy detects the change
        config = copy.deepcopy(provider.config) if provider.config else {}

        # Handle package pricing (for providers like Mattermost with bulk licenses)
        if package_pricing and package_pricing.get("cost"):
            config["package_pricing"] = package_pricing

            # Calculate monthly package cost
            package_cost = Decimal(package_pricing["cost"])
            billing_cycle = package_pricing.get("billing_cycle", "yearly")
            if billing_cycle == "yearly":
                monthly_package_cost = package_cost / 12
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
                    currency=package_pricing.get("currency", "EUR"),
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

    async def update_individual_license_pricing(
        self,
        provider_id: UUID,
        individual_pricing_config: dict,
    ) -> None:
        """Update individual license type pricing (for combined license types).

        For combined license types, the total monthly cost is calculated as the sum of
        individual license prices. For example, if a user has "E5, Power BI, Teams":
        - E5 = 30 EUR/month
        - Power BI = 10 EUR/month
        - Teams = 0 EUR/month (free)
        - Total = 40 EUR/month

        Args:
            provider_id: Provider UUID
            individual_pricing_config: Dict of license_type -> pricing info
        """
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

    @staticmethod
    def calculate_monthly_cost(cost: Decimal, billing_cycle: str) -> Decimal:
        """Calculate monthly cost from billing cycle.

        Args:
            cost: Raw cost amount
            billing_cycle: Billing cycle (yearly, monthly, perpetual, one_time)

        Returns:
            Monthly equivalent cost
        """
        if billing_cycle == "yearly":
            return cost / 12
        elif billing_cycle == "monthly":
            return cost
        else:
            # perpetual/one_time - no recurring monthly cost
            return Decimal("0")

    @staticmethod
    def build_pricing_config_dict(pricing_list: list) -> dict:
        """Build pricing config dictionary from a list of pricing objects.

        Args:
            pricing_list: List of pricing objects with license_type, cost, etc.

        Returns:
            Dict mapping license_type to pricing info
        """
        pricing_config = {}
        for p in pricing_list:
            if hasattr(p, "cost") and p.cost and p.cost != "0":
                pricing_config[p.license_type] = {
                    "cost": p.cost,
                    "currency": getattr(p, "currency", "EUR"),
                    "billing_cycle": getattr(p, "billing_cycle", "yearly"),
                    "payment_frequency": getattr(p, "payment_frequency", "yearly"),
                    "display_name": getattr(p, "display_name", None),
                    "next_billing_date": getattr(p, "next_billing_date", None),
                    "notes": getattr(p, "notes", None),
                }
        return pricing_config
