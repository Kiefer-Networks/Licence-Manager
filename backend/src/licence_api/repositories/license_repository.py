"""License repository."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.provider import ProviderORM
from licence_api.repositories.base import BaseRepository
from licence_api.utils.validation import escape_like_wildcards


class LicenseRepository(BaseRepository[LicenseORM]):
    """Repository for license operations."""

    model = LicenseORM

    async def get_by_provider_and_external_id(
        self,
        provider_id: UUID,
        external_user_id: str,
    ) -> LicenseORM | None:
        """Get license by provider and external user ID.

        Args:
            provider_id: Provider UUID
            external_user_id: External user ID in provider system

        Returns:
            LicenseORM or None if not found
        """
        result = await self.session.execute(
            select(LicenseORM).where(
                and_(
                    LicenseORM.provider_id == provider_id,
                    LicenseORM.external_user_id == external_user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_all_with_details(
        self,
        provider_id: UUID | None = None,
        employee_id: UUID | None = None,
        status: str | None = None,
        unassigned_only: bool = False,
        search: str | None = None,
        department: str | None = None,
        sort_by: str = "synced_at",
        sort_dir: str = "desc",
        offset: int = 0,
        limit: int = 100,
        external_only: bool = False,
        company_domains: list[str] | None = None,
        service_accounts_only: bool = False,
        admin_accounts_only: bool = False,
        admin_account_owner_id: UUID | None = None,
    ) -> tuple[list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]], int]:
        """Get licenses with provider and employee details.

        Args:
            provider_id: Filter by provider
            employee_id: Filter by employee
            status: Filter by status
            unassigned_only: Only return licenses without employee
            search: Search by external_user_id, employee email or name
            department: Filter by employee department
            sort_by: Column to sort by
            sort_dir: Sort direction (asc/desc)
            offset: Pagination offset
            limit: Pagination limit
            external_only: Only return licenses with external emails
            company_domains: Company domains for external email detection
            service_accounts_only: Only return licenses marked as service accounts
            admin_accounts_only: Only return licenses marked as admin accounts
            admin_account_owner_id: Filter by admin account owner (employee ID)

        Returns:
            Tuple of (license details, total count)
        """
        query = (
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
        )
        count_query = (
            select(func.count())
            .select_from(LicenseORM)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
        )

        if provider_id:
            query = query.where(LicenseORM.provider_id == provider_id)
            count_query = count_query.where(LicenseORM.provider_id == provider_id)

        if employee_id:
            query = query.where(LicenseORM.employee_id == employee_id)
            count_query = count_query.where(LicenseORM.employee_id == employee_id)

        if status:
            query = query.where(LicenseORM.status == status)
            count_query = count_query.where(LicenseORM.status == status)

        if unassigned_only:
            query = query.where(LicenseORM.employee_id.is_(None))
            count_query = count_query.where(LicenseORM.employee_id.is_(None))
            # Exclude service accounts from unassigned list - they are intentionally unassigned
            query = query.where(LicenseORM.is_service_account == False)
            count_query = count_query.where(LicenseORM.is_service_account == False)

        if service_accounts_only:
            query = query.where(LicenseORM.is_service_account == True)
            count_query = count_query.where(LicenseORM.is_service_account == True)

        if admin_accounts_only:
            query = query.where(LicenseORM.is_admin_account == True)
            count_query = count_query.where(LicenseORM.is_admin_account == True)

        if admin_account_owner_id:
            query = query.where(LicenseORM.admin_account_owner_id == admin_account_owner_id)
            count_query = count_query.where(LicenseORM.admin_account_owner_id == admin_account_owner_id)

        if department:
            query = query.where(EmployeeORM.department == department)
            count_query = count_query.where(EmployeeORM.department == department)

        if search:
            # Escape LIKE wildcards to prevent pattern injection
            search_pattern = f"%{escape_like_wildcards(search.lower())}%"
            search_filter = or_(
                LicenseORM.external_user_id.ilike(search_pattern, escape="\\"),
                EmployeeORM.email.ilike(search_pattern, escape="\\"),
                EmployeeORM.full_name.ilike(search_pattern, escape="\\"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # External email filter - filter at SQL level for performance
        if external_only and company_domains:
            # Must have @ sign (be an email-like identifier)
            email_condition = LicenseORM.external_user_id.like("%@%")
            # Must NOT match any company domain
            # Escape SQL wildcards in domains to prevent injection
            domain_conditions = [
                ~LicenseORM.external_user_id.ilike(f"%@{escape_like_wildcards(domain)}", escape="\\")
                for domain in company_domains
            ]
            # Also exclude subdomain matches (e.g., @sub.company.com)
            subdomain_conditions = [
                ~LicenseORM.external_user_id.ilike(f"%@%.{escape_like_wildcards(domain)}", escape="\\")
                for domain in company_domains
            ]
            external_filter = and_(
                email_condition,
                *domain_conditions,
                *subdomain_conditions,
            )
            query = query.where(external_filter)
            count_query = count_query.where(external_filter)

        # Validated sorting - whitelist of allowed columns
        sort_columns = {
            "synced_at": LicenseORM.synced_at,
            "external_user_id": LicenseORM.external_user_id,
            "license_type": LicenseORM.license_type,
            "status": LicenseORM.status,
            "last_activity_at": LicenseORM.last_activity_at,
            "monthly_cost": LicenseORM.monthly_cost,
            "provider_name": ProviderORM.display_name,
            "employee_name": EmployeeORM.full_name,
        }
        sort_column = sort_columns.get(sort_by, LicenseORM.synced_at)

        # Validate sort direction
        if sort_dir not in ("asc", "desc"):
            sort_dir = "desc"

        if sort_dir == "desc":
            query = query.order_by(sort_column.desc().nulls_last())
        else:
            query = query.order_by(sort_column.asc().nulls_last())

        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        licenses = list(result.all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return licenses, total

    async def get_inactive(
        self,
        days_threshold: int = 30,
        department: str | None = None,
        provider_id: UUID | None = None,
        limit: int = 100,
    ) -> list[tuple[LicenseORM, ProviderORM, EmployeeORM | None]]:
        """Get licenses with no activity for specified days.

        Args:
            days_threshold: Number of days without activity
            department: Filter by employee department
            provider_id: Filter by provider UUID
            limit: Maximum results

        Returns:
            List of inactive licenses with details
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_threshold)

        query = (
            select(LicenseORM, ProviderORM, EmployeeORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            .where(LicenseORM.status == "active")
            .where(
                (LicenseORM.last_activity_at < cutoff)
                | (LicenseORM.last_activity_at.is_(None))
            )
        )

        if department:
            query = query.where(EmployeeORM.department == department)

        if provider_id:
            query = query.where(LicenseORM.provider_id == provider_id)

        query = query.order_by(LicenseORM.last_activity_at.asc().nulls_first()).limit(limit)

        result = await self.session.execute(query)
        return list(result.all())

    async def get_by_employee(self, employee_id: UUID) -> list[LicenseORM]:
        """Get all licenses for an employee.

        Args:
            employee_id: Employee UUID

        Returns:
            List of licenses
        """
        result = await self.session.execute(
            select(LicenseORM).where(LicenseORM.employee_id == employee_id)
        )
        return list(result.scalars().all())

    async def upsert(
        self,
        provider_id: UUID,
        external_user_id: str,
        employee_id: UUID | None,
        license_type: str | None,
        status: str,
        assigned_at: datetime | None,
        last_activity_at: datetime | None,
        monthly_cost: Decimal | None,
        currency: str,
        metadata: dict[str, Any] | None,
        synced_at: datetime,
    ) -> LicenseORM:
        """Create or update license by provider and external ID.

        Args:
            provider_id: Provider UUID
            external_user_id: External user ID
            employee_id: Employee UUID (optional)
            license_type: License type
            status: License status
            assigned_at: Assignment date
            last_activity_at: Last activity date
            monthly_cost: Monthly cost
            currency: Currency code
            metadata: Additional metadata
            synced_at: Sync timestamp

        Returns:
            Created or updated LicenseORM
        """
        existing = await self.get_by_provider_and_external_id(provider_id, external_user_id)

        if existing:
            existing.employee_id = employee_id
            existing.license_type = license_type
            existing.status = status
            existing.assigned_at = assigned_at
            existing.last_activity_at = last_activity_at
            existing.monthly_cost = monthly_cost
            existing.currency = currency
            existing.extra_data = metadata
            existing.synced_at = synced_at
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            provider_id=provider_id,
            external_user_id=external_user_id,
            employee_id=employee_id,
            license_type=license_type,
            status=status,
            assigned_at=assigned_at,
            last_activity_at=last_activity_at,
            monthly_cost=monthly_cost,
            currency=currency,
            extra_data=metadata,
            synced_at=synced_at,
        )

    async def get_statistics(self, department: str | None = None) -> dict[str, Any]:
        """Get license statistics.

        Args:
            department: Optional department filter

        Returns:
            Dict with license statistics
        """
        # Base queries - join with employee for department filter
        base_query = select(func.count()).select_from(LicenseORM)
        if department:
            base_query = base_query.join(
                EmployeeORM, LicenseORM.employee_id == EmployeeORM.id
            ).where(EmployeeORM.department == department)

        # Total count
        total_result = await self.session.execute(base_query)
        total = total_result.scalar_one()

        # Count by status
        status_query = select(LicenseORM.status, func.count()).group_by(LicenseORM.status)
        if department:
            status_query = status_query.join(
                EmployeeORM, LicenseORM.employee_id == EmployeeORM.id
            ).where(EmployeeORM.department == department)
        status_result = await self.session.execute(status_query)
        by_status = dict(status_result.all())

        # Unassigned count and potential savings (only if no department filter)
        if department:
            unassigned = 0
            potential_savings = Decimal("0")
        else:
            unassigned_result = await self.session.execute(
                select(func.count())
                .select_from(LicenseORM)
                .where(LicenseORM.employee_id.is_(None))
            )
            unassigned = unassigned_result.scalar_one()

            # Potential savings = sum of monthly_cost for all unassigned licenses
            savings_result = await self.session.execute(
                select(func.sum(LicenseORM.monthly_cost))
                .select_from(LicenseORM)
                .where(LicenseORM.employee_id.is_(None))
            )
            potential_savings = savings_result.scalar_one() or Decimal("0")

        # Total monthly cost - include all licenses regardless of status
        # (unassigned licenses still cost money)
        cost_query = (
            select(func.sum(LicenseORM.monthly_cost))
            .select_from(LicenseORM)
        )
        if department:
            cost_query = cost_query.join(
                EmployeeORM, LicenseORM.employee_id == EmployeeORM.id
            ).where(EmployeeORM.department == department)
        cost_result = await self.session.execute(cost_query)
        total_cost = cost_result.scalar_one() or Decimal("0")

        return {
            "total": total,
            "by_status": by_status,
            "unassigned": unassigned,
            "potential_savings": potential_savings,
            "total_monthly_cost": total_cost,
        }

    async def count_by_provider(self) -> dict[UUID, int]:
        """Count licenses by provider.

        Returns:
            Dict mapping provider ID to count
        """
        result = await self.session.execute(
            select(LicenseORM.provider_id, func.count())
            .group_by(LicenseORM.provider_id)
        )
        return dict(result.all())

    async def count_by_employee_ids(self, employee_ids: list[UUID]) -> dict[UUID, int]:
        """Count licenses for multiple employees in a single query (batch).

        This avoids N+1 query problems when listing employees with license counts.

        Args:
            employee_ids: List of employee UUIDs

        Returns:
            Dict mapping employee ID to license count
        """
        if not employee_ids:
            return {}

        result = await self.session.execute(
            select(LicenseORM.employee_id, func.count())
            .where(LicenseORM.employee_id.in_(employee_ids))
            .group_by(LicenseORM.employee_id)
        )
        return dict(result.all())

    async def count_admin_accounts_by_owner_ids(self, owner_ids: list[UUID]) -> dict[UUID, int]:
        """Count admin accounts for multiple owners in a single query (batch).

        This counts licenses where admin_account_owner_id matches the owner IDs.

        Args:
            owner_ids: List of employee UUIDs who own admin accounts

        Returns:
            Dict mapping owner ID to admin account count
        """
        if not owner_ids:
            return {}

        result = await self.session.execute(
            select(LicenseORM.admin_account_owner_id, func.count())
            .where(LicenseORM.admin_account_owner_id.in_(owner_ids))
            .where(LicenseORM.is_admin_account == True)
            .group_by(LicenseORM.admin_account_owner_id)
        )
        return dict(result.all())

    async def get_licenses_with_providers_for_employees(
        self,
        employee_ids: list[UUID],
    ) -> dict[UUID, list[tuple[Any, Any]]]:
        """Get licenses with provider names for multiple employees in a single query.

        This avoids N+1 query problems when generating offboarding reports.

        Args:
            employee_ids: List of employee UUIDs

        Returns:
            Dict mapping employee ID to list of (license, provider) tuples
        """
        if not employee_ids:
            return {}

        result = await self.session.execute(
            select(LicenseORM, ProviderORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .where(LicenseORM.employee_id.in_(employee_ids))
        )

        # Group by employee_id
        grouped: dict[UUID, list[tuple[Any, Any]]] = {}
        for lic, provider in result.all():
            if lic.employee_id not in grouped:
                grouped[lic.employee_id] = []
            grouped[lic.employee_id].append((lic, provider))

        return grouped

    async def get_by_ids_with_providers(
        self,
        license_ids: list[UUID],
    ) -> list[tuple[LicenseORM, ProviderORM]]:
        """Get multiple licenses by IDs with their providers.

        Args:
            license_ids: List of license UUIDs

        Returns:
            List of (license, provider) tuples
        """
        if not license_ids:
            return []

        result = await self.session.execute(
            select(LicenseORM, ProviderORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .where(LicenseORM.id.in_(license_ids))
        )
        return list(result.all())

    async def delete_by_ids(self, license_ids: list[UUID]) -> int:
        """Delete multiple licenses by IDs.

        Args:
            license_ids: List of license UUIDs to delete

        Returns:
            Number of deleted licenses
        """
        if not license_ids:
            return 0

        from sqlalchemy import delete

        result = await self.session.execute(
            delete(LicenseORM).where(LicenseORM.id.in_(license_ids))
        )
        await self.session.flush()
        return result.rowcount

    async def unassign_by_ids(self, license_ids: list[UUID]) -> int:
        """Bulk unassign licenses (set employee_id = NULL).

        Args:
            license_ids: List of license UUIDs to unassign

        Returns:
            Number of unassigned licenses
        """
        if not license_ids:
            return 0

        from sqlalchemy import update

        result = await self.session.execute(
            update(LicenseORM)
            .where(LicenseORM.id.in_(license_ids))
            .values(employee_id=None)
        )
        await self.session.flush()
        return result.rowcount

    async def get_license_type_counts(self, provider_id: UUID) -> dict[str, int]:
        """Get counts of each license type for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Dict mapping license_type to count
        """
        result = await self.session.execute(
            select(LicenseORM.license_type, func.count())
            .where(LicenseORM.provider_id == provider_id)
            .where(LicenseORM.license_type.isnot(None))
            .group_by(LicenseORM.license_type)
        )
        return {lt or "Unknown": count for lt, count in result.all()}

    async def get_individual_license_type_counts(
        self,
        provider_id: UUID,
    ) -> dict[str, int]:
        """Get counts of individual license types extracted from combined strings.

        For providers like Microsoft 365 where users can have multiple licenses
        (stored as comma-separated like "E5, Power BI, Teams"), this extracts
        and counts each individual license type.

        Args:
            provider_id: Provider UUID

        Returns:
            Dict mapping individual license_type to count of users with that license
        """
        # First get all license_type strings
        result = await self.session.execute(
            select(LicenseORM.license_type)
            .where(LicenseORM.provider_id == provider_id)
            .where(LicenseORM.license_type.isnot(None))
        )

        # Count individual license types
        individual_counts: dict[str, int] = {}
        for (license_type,) in result.all():
            if not license_type:
                continue
            # Split by comma and strip whitespace
            for individual in license_type.split(","):
                individual = individual.strip()
                if individual:
                    individual_counts[individual] = individual_counts.get(individual, 0) + 1

        return individual_counts

    async def update_pricing_by_individual_type(
        self,
        provider_id: UUID,
        individual_pricing: dict[str, tuple[Decimal | None, str]],
    ) -> int:
        """Update pricing for all licenses based on individual license type prices.

        For combined license types (e.g., "E5, Power BI, Teams"), calculates the
        total price as the sum of individual license prices.

        Args:
            provider_id: Provider UUID
            individual_pricing: Dict mapping individual license type to (price, currency)

        Returns:
            Number of updated licenses
        """
        from sqlalchemy import update

        # Get all licenses for this provider
        result = await self.session.execute(
            select(LicenseORM.id, LicenseORM.license_type)
            .where(LicenseORM.provider_id == provider_id)
            .where(LicenseORM.license_type.isnot(None))
        )

        # Pre-calculate all updates to batch them
        updates_by_cost: dict[tuple[Decimal | None, str], list[UUID]] = {}
        for license_id, license_type in result.all():
            if not license_type:
                continue

            # Calculate total cost from individual prices
            total_cost = Decimal("0")
            currency = "EUR"  # Default currency

            for individual in license_type.split(","):
                individual = individual.strip()
                if individual and individual in individual_pricing:
                    price, curr = individual_pricing[individual]
                    if price:
                        total_cost += price
                        currency = curr  # Use the last currency

            # Group by cost/currency for batch update
            cost_key = (total_cost if total_cost > 0 else None, currency)
            if cost_key not in updates_by_cost:
                updates_by_cost[cost_key] = []
            updates_by_cost[cost_key].append(license_id)

        # Batch update by cost group (reduces N updates to M updates where M = unique cost values)
        updated_count = 0
        for (monthly_cost, currency), license_ids in updates_by_cost.items():
            if license_ids:
                await self.session.execute(
                    update(LicenseORM)
                    .where(LicenseORM.id.in_(license_ids))
                    .values(monthly_cost=monthly_cost, currency=currency)
                )
                updated_count += len(license_ids)

        await self.session.flush()
        return updated_count

    async def update_pricing_by_type(
        self,
        provider_id: UUID,
        license_type: str,
        monthly_cost: Decimal | None,
        currency: str = "EUR",
    ) -> int:
        """Update pricing for all licenses of a specific type.

        Args:
            provider_id: Provider UUID
            license_type: License type to update
            monthly_cost: New monthly cost
            currency: Currency code

        Returns:
            Number of updated licenses
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(LicenseORM)
            .where(
                and_(
                    LicenseORM.provider_id == provider_id,
                    LicenseORM.license_type == license_type,
                )
            )
            .values(monthly_cost=monthly_cost, currency=currency)
        )
        await self.session.flush()
        return result.rowcount

    async def update_all_active_pricing(
        self,
        provider_id: UUID,
        monthly_cost: Decimal | None,
        currency: str = "EUR",
    ) -> int:
        """Update pricing for all active licenses of a provider.

        Used for package pricing where all licenses share the same cost.

        Args:
            provider_id: Provider UUID
            monthly_cost: New monthly cost per license
            currency: Currency code

        Returns:
            Number of updated licenses
        """
        from sqlalchemy import update

        result = await self.session.execute(
            update(LicenseORM)
            .where(
                and_(
                    LicenseORM.provider_id == provider_id,
                    LicenseORM.status == "active",
                )
            )
            .values(monthly_cost=monthly_cost, currency=currency)
        )
        await self.session.flush()
        return result.rowcount

    async def count_active_by_provider(self, provider_id: UUID) -> int:
        """Count active licenses for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Number of active licenses
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count())
            .select_from(LicenseORM)
            .where(
                and_(
                    LicenseORM.provider_id == provider_id,
                    LicenseORM.status == "active",
                )
            )
        )
        return result.scalar() or 0

    async def get_stats_by_provider(
        self,
        company_domains: list[str],
    ) -> dict[UUID, dict[str, int]]:
        """Get license statistics grouped by provider.

        Args:
            company_domains: List of company email domains (lowercase)

        Returns:
            Dict mapping provider_id to stats dict with:
            - active: count of active licenses
            - assigned: count of active licenses with employee_id
            - not_in_hris: count of active licenses with internal user not found in HRIS
            - unassigned: count of active licenses with no user assigned
            - external: count of active external licenses
        """
        from sqlalchemy import func, case

        # Build domain matching condition for external detection
        # A license is external if its email doesn't end with any company domain
        # We use external_user_id as the email field

        results = await self.session.execute(
            select(
                LicenseORM.provider_id,
                func.count().filter(LicenseORM.status == "active").label("active"),
                func.count().filter(
                    and_(
                        LicenseORM.status == "active",
                        LicenseORM.employee_id.isnot(None),
                    )
                ).label("assigned"),
            )
            .group_by(LicenseORM.provider_id)
        )

        stats: dict[UUID, dict[str, int]] = {}
        for row in results:
            stats[row.provider_id] = {
                "active": row.active or 0,
                "assigned": row.assigned or 0,
                "not_in_hris": 0,
                "unassigned": 0,
                "external": 0,
            }

        # For external/not_in_hris detection, we need to check each license's email
        # This is a bit expensive but necessary for accurate stats
        # Only fetch active licenses without employee_id, excluding service accounts
        # (service accounts are intentionally unassigned and should not count as problems)
        # Also exclude licenses with suggested_employee_id (these are "suggested", not "external")
        unassigned_results = await self.session.execute(
            select(LicenseORM.provider_id, LicenseORM.external_user_id, LicenseORM.match_status)
            .where(
                and_(
                    LicenseORM.status == "active",
                    LicenseORM.employee_id.is_(None),
                    LicenseORM.is_service_account == False,
                    LicenseORM.suggested_employee_id.is_(None),  # Exclude suggested matches
                )
            )
        )

        for row in unassigned_results:
            provider_id = row.provider_id
            email = (row.external_user_id or "").lower()
            match_status = row.match_status

            if provider_id not in stats:
                stats[provider_id] = {"active": 0, "assigned": 0, "not_in_hris": 0, "unassigned": 0, "external": 0}

            # Check if license has no user assigned:
            # - empty external_user_id, OR
            # - external_user_id is not an email (no @ sign) - e.g., license keys
            if not email or "@" not in email:
                stats[provider_id]["unassigned"] += 1
                continue

            # At this point, email contains @, so it's an actual email address
            # Check if external - either by match_status or by domain check
            is_external = match_status in ("external_review", "external_guest")
            if not is_external:
                domain = email.split("@")[1]
                if not any(domain == d or domain.endswith("." + d) for d in company_domains):
                    is_external = True

            if is_external:
                stats[provider_id]["external"] += 1
            else:
                stats[provider_id]["not_in_hris"] += 1

        return stats

    async def get_assigned_counts_by_provider_and_type(
        self,
    ) -> dict[tuple[str, str | None], int]:
        """Get counts of assigned licenses grouped by provider_id and license_type.

        Used for utilization reporting to compare purchased seats vs assigned seats.

        Returns:
            Dict mapping (provider_id_str, license_type) to count of assigned licenses
        """
        result = await self.session.execute(
            select(
                LicenseORM.provider_id,
                LicenseORM.license_type,
                func.count(),
            )
            .where(LicenseORM.status == "active")
            .group_by(LicenseORM.provider_id, LicenseORM.license_type)
        )

        counts: dict[tuple[str, str | None], int] = {}
        for provider_id, license_type, count in result.all():
            key = (str(provider_id), license_type)
            counts[key] = count

        return counts

    async def get_assigned_counts_by_provider(self) -> dict[str, int]:
        """Get counts of active licenses grouped by provider_id only.

        Used for utilization reporting when no license_type distinction is needed
        (e.g., when using provider_license_info fallback).

        Returns:
            Dict mapping provider_id_str to count of active licenses
        """
        result = await self.session.execute(
            select(
                LicenseORM.provider_id,
                func.count(),
            )
            .where(LicenseORM.status == "active")
            .group_by(LicenseORM.provider_id)
        )

        counts: dict[str, int] = {}
        for provider_id, count in result.all():
            counts[str(provider_id)] = count

        return counts

    async def count_external_licenses(
        self,
        company_domains: list[str],
        department: str | None = None,
        exclude_provider_name: str | None = "hibob",
    ) -> int:
        """Count licenses with external email addresses at the SQL level.

        This is optimized for dashboard statistics, avoiding full table scans.

        Args:
            company_domains: List of company domains (emails matching these are internal)
            department: Optional department filter
            exclude_provider_name: Provider name to exclude (default: hibob for HRIS)

        Returns:
            Count of external licenses
        """
        if not company_domains:
            return 0

        # Build the base query
        query = (
            select(func.count())
            .select_from(LicenseORM)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
        )

        if department:
            query = query.outerjoin(EmployeeORM, LicenseORM.employee_id == EmployeeORM.id)
            query = query.where(EmployeeORM.department == department)

        # Exclude specified provider (e.g., hibob which is HRIS source)
        if exclude_provider_name:
            query = query.where(ProviderORM.name != exclude_provider_name)

        # Must have @ sign (be an email-like identifier)
        query = query.where(LicenseORM.external_user_id.like("%@%"))

        # Must NOT match any company domain
        # Escape SQL wildcards in domains to prevent injection
        for domain in company_domains:
            escaped_domain = escape_like_wildcards(domain)
            query = query.where(~LicenseORM.external_user_id.ilike(f"%@{escaped_domain}", escape="\\"))
            query = query.where(~LicenseORM.external_user_id.ilike(f"%@%.{escaped_domain}", escape="\\"))

        result = await self.session.execute(query)
        return result.scalar_one()

    # =========================================================================
    # Expiration and lifecycle methods (MVC-02 fix)
    # =========================================================================

    async def get_expired_needing_update(
        self,
        today: "date",
        excluded_statuses: list[str],
    ) -> list[LicenseORM]:
        """Get licenses that have expired but status not yet updated.

        Args:
            today: Current date
            excluded_statuses: Statuses to exclude (already expired/cancelled)

        Returns:
            List of licenses needing status update
        """
        from datetime import date
        result = await self.session.execute(
            select(LicenseORM).where(
                and_(
                    LicenseORM.expires_at.isnot(None),
                    LicenseORM.expires_at < today,
                    LicenseORM.status.notin_(excluded_statuses),
                )
            )
        )
        return list(result.scalars().all())

    async def get_cancelled_needing_update(
        self,
        today: "date",
        excluded_status: str,
    ) -> list[LicenseORM]:
        """Get licenses with passed cancellation date but status not yet updated.

        Args:
            today: Current date
            excluded_status: Status to exclude (already cancelled)

        Returns:
            List of licenses needing status update
        """
        from datetime import date
        result = await self.session.execute(
            select(LicenseORM).where(
                and_(
                    LicenseORM.cancellation_effective_date.isnot(None),
                    LicenseORM.cancellation_effective_date <= today,
                    LicenseORM.status != excluded_status,
                )
            )
        )
        return list(result.scalars().all())

    async def get_orphaned_admin_accounts(
        self,
    ) -> list[tuple[LicenseORM, EmployeeORM, ProviderORM]]:
        """Get admin account licenses where owner is offboarded.

        Returns:
            List of tuples (license, employee, provider)
        """
        result = await self.session.execute(
            select(LicenseORM, EmployeeORM, ProviderORM)
            .join(EmployeeORM, LicenseORM.admin_account_owner_id == EmployeeORM.id)
            .join(ProviderORM, LicenseORM.provider_id == ProviderORM.id)
            .where(
                LicenseORM.is_admin_account == True,
                LicenseORM.admin_account_owner_id.isnot(None),
                EmployeeORM.status == "offboarded",
            )
        )
        return list(result.all())
