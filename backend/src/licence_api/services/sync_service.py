"""Sync service for orchestrating provider synchronization."""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import AVATAR_DIR
from licence_api.models.domain.provider import ProviderName, SyncStatus
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.service_account_pattern_repository import ServiceAccountPatternRepository
from licence_api.repositories.admin_account_pattern_repository import AdminAccountPatternRepository
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.encryption import get_encryption_service
from licence_api.services.matching_service import MatchingService
from licence_api.utils.secure_logging import log_error, log_warning

logger = logging.getLogger(__name__)


class SyncService:
    """Service for synchronizing data from providers."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.provider_repo = ProviderRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.license_repo = LicenseRepository(session)
        self.svc_account_pattern_repo = ServiceAccountPatternRepository(session)
        self.admin_account_pattern_repo = AdminAccountPatternRepository(session)
        self.encryption = get_encryption_service()

    async def sync_all_providers(self) -> dict[str, Any]:
        """Sync all enabled providers.

        Returns:
            Dict with sync results
        """
        providers = await self.provider_repo.get_enabled()
        results = {}

        for provider in providers:
            try:
                result = await self.sync_provider(provider.id)
                results[provider.name] = result
            except Exception as e:
                log_error(logger, f"Error syncing provider {provider.name}", e)
                results[provider.name] = {"error": "Sync operation failed"}
                await self.provider_repo.update_sync_status(
                    provider.id,
                    SyncStatus.FAILED,
                )

        return results

    async def sync_provider(self, provider_id: UUID) -> dict[str, Any]:
        """Sync a single provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Dict with sync results
        """
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError(f"Provider not found: {provider_id}")

        # Update status to in progress
        await self.provider_repo.update_sync_status(
            provider_id,
            SyncStatus.IN_PROGRESS,
        )

        try:
            # Manual providers don't need sync - data is entered manually
            if provider.name == ProviderName.MANUAL:
                logger.info(f"Skipping sync for manual provider {provider_id}")
                await self.provider_repo.update_sync_status(
                    provider_id,
                    SyncStatus.SUCCESS,
                    datetime.now(timezone.utc),
                )
                return {
                    "provider": "manual",
                    "skipped": True,
                    "reason": "Manual providers do not sync from external APIs",
                }

            # Decrypt credentials
            credentials = self.encryption.decrypt(provider.credentials_encrypted)

            # Get the appropriate provider implementation
            provider_impl = self._get_provider_implementation(
                ProviderName(provider.name),
                credentials,
            )

            # Sync based on provider type
            if provider.name == ProviderName.HIBOB:
                result = await self._sync_hibob(provider_impl, provider_id)
            elif provider.name == ProviderName.PERSONIO:
                result = await self._sync_personio(provider_impl, provider_id)
            else:
                result = await self._sync_license_provider(provider_impl, provider_id)

            # Update status to success
            await self.provider_repo.update_sync_status(
                provider_id,
                SyncStatus.SUCCESS,
                datetime.now(timezone.utc),
            )

            return result

        except Exception as e:
            log_error(logger, f"Error syncing provider {provider.name}", e)
            await self.provider_repo.update_sync_status(
                provider_id,
                SyncStatus.FAILED,
            )
            raise

    def _get_provider_implementation(
        self,
        name: ProviderName,
        credentials: dict[str, Any],
    ):
        """Get provider implementation instance.

        Args:
            name: Provider name
            credentials: Decrypted credentials

        Returns:
            Provider implementation instance
        """
        from licence_api.providers import (
            AdobeProvider,
            AnthropicProvider,
            AtlassianProvider,
            Auth0Provider,
            CursorProvider,
            FigmaProvider,
            GitHubProvider,
            GitLabProvider,
            GoogleWorkspaceProvider,
            HiBobProvider,
            JetBrainsProvider,
            MailjetProvider,
            MattermostProvider,
            MicrosoftProvider,
            MiroProvider,
            OnePasswordProvider,
            OpenAIProvider,
            PersonioProvider,
            SlackProvider,
        )

        providers = {
            ProviderName.ADOBE: AdobeProvider,
            ProviderName.ANTHROPIC: AnthropicProvider,
            ProviderName.ATLASSIAN: AtlassianProvider,
            ProviderName.AUTH0: Auth0Provider,
            ProviderName.CURSOR: CursorProvider,
            ProviderName.FIGMA: FigmaProvider,
            ProviderName.GITHUB: GitHubProvider,
            ProviderName.GITLAB: GitLabProvider,
            ProviderName.GOOGLE_WORKSPACE: GoogleWorkspaceProvider,
            ProviderName.HIBOB: HiBobProvider,
            ProviderName.JETBRAINS: JetBrainsProvider,
            ProviderName.MAILJET: MailjetProvider,
            ProviderName.MATTERMOST: MattermostProvider,
            ProviderName.MICROSOFT: MicrosoftProvider,
            ProviderName.MIRO: MiroProvider,
            ProviderName.ONEPASSWORD: OnePasswordProvider,
            ProviderName.OPENAI: OpenAIProvider,
            ProviderName.PERSONIO: PersonioProvider,
            ProviderName.SLACK: SlackProvider,
        }

        provider_class = providers.get(name)
        if provider_class is None:
            raise ValueError(f"Unknown provider: {name}")

        return provider_class(credentials)

    async def _sync_hibob(
        self,
        provider,
        provider_id: UUID,
    ) -> dict[str, Any]:
        """Sync employees from HiBob.

        Args:
            provider: HiBob provider instance
            provider_id: Provider UUID

        Returns:
            Dict with sync results
        """
        employees = await provider.fetch_employees()
        synced_at = datetime.now(timezone.utc)
        created = 0
        updated = 0

        for emp_data in employees:
            existing = await self.employee_repo.get_by_hibob_id(emp_data["hibob_id"])
            await self.employee_repo.upsert(
                hibob_id=emp_data["hibob_id"],
                email=emp_data["email"],
                full_name=emp_data["full_name"],
                department=emp_data.get("department"),
                status=emp_data["status"],
                start_date=emp_data.get("start_date"),
                termination_date=emp_data.get("termination_date"),
                synced_at=synced_at,
                manager_email=emp_data.get("manager_email"),
            )
            if existing:
                updated += 1
            else:
                created += 1

        # Resolve manager relationships after all employees are synced
        managers_resolved = await self.employee_repo.resolve_manager_ids()
        logger.info(f"Resolved {managers_resolved} manager relationships")

        # Sync avatars after employee data
        avatar_result = await self._sync_avatars(provider, employees)

        return {
            "provider": "hibob",
            "employees_created": created,
            "employees_updated": updated,
            "total": len(employees),
            "managers_resolved": managers_resolved,
            "avatars": avatar_result,
        }

    async def _sync_personio(
        self,
        provider,
        provider_id: UUID,
    ) -> dict[str, Any]:
        """Sync employees from Personio.

        Args:
            provider: Personio provider instance
            provider_id: Provider UUID

        Returns:
            Dict with sync results
        """
        employees = await provider.fetch_employees()
        synced_at = datetime.now(timezone.utc)
        created = 0
        updated = 0

        for emp_data in employees:
            existing = await self.employee_repo.get_by_hibob_id(emp_data["hibob_id"])
            await self.employee_repo.upsert(
                hibob_id=emp_data["hibob_id"],
                email=emp_data["email"],
                full_name=emp_data["full_name"],
                department=emp_data.get("department"),
                status=emp_data["status"],
                start_date=emp_data.get("start_date"),
                termination_date=emp_data.get("termination_date"),
                synced_at=synced_at,
                manager_email=emp_data.get("manager_email"),
            )
            if existing:
                updated += 1
            else:
                created += 1

        # Resolve manager relationships after all employees are synced
        managers_resolved = await self.employee_repo.resolve_manager_ids()
        logger.info(f"Resolved {managers_resolved} manager relationships")

        return {
            "provider": "personio",
            "employees_created": created,
            "employees_updated": updated,
            "total": len(employees),
            "managers_resolved": managers_resolved,
        }

    async def _sync_avatars(
        self,
        provider,
        employees: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Sync employee avatars from HiBob.

        Downloads avatars with intelligent rate limiting:
        - Base delay between requests
        - Exponential backoff on 429 errors
        - Batch pauses every N requests

        Args:
            provider: HiBob provider instance
            employees: List of employee data dicts

        Returns:
            Dict with avatar sync results
        """
        # Ensure avatar directory exists
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        skipped = 0
        failed = 0
        rate_limited = 0

        # Rate limiting configuration
        base_delay = 1.0  # 1 second between requests
        batch_size = 50  # Pause after every N requests
        batch_pause = 30.0  # 30 second pause between batches
        max_retries = 3

        requests_in_batch = 0

        for emp_data in employees:
            hibob_id = emp_data["hibob_id"]
            avatar_path = AVATAR_DIR / f"{hibob_id}.jpg"

            # Skip if avatar already exists
            if avatar_path.exists():
                skipped += 1
                continue

            # Batch pause to avoid rate limiting
            if requests_in_batch >= batch_size:
                logger.info(f"Batch pause: waiting {batch_pause}s after {batch_size} requests")
                await asyncio.sleep(batch_pause)
                requests_in_batch = 0

            # Retry loop with exponential backoff
            for attempt in range(max_retries):
                try:
                    # Base delay between requests
                    await asyncio.sleep(base_delay)

                    avatar_bytes = await provider.fetch_avatar(hibob_id)
                    requests_in_batch += 1

                    if avatar_bytes:
                        avatar_path.write_bytes(avatar_bytes)
                        downloaded += 1
                        if downloaded % 10 == 0:
                            logger.info(f"Avatar progress: {downloaded} downloaded, {skipped} skipped")
                    else:
                        # Could be 429 or no avatar - check if we should retry
                        failed += 1
                    break  # Success or definite failure, exit retry loop

                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "too many" in error_msg:
                        rate_limited += 1
                        backoff = base_delay * (2 ** attempt) * 10  # Exponential backoff
                        logger.warning(f"Rate limited for {hibob_id}, waiting {backoff}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(backoff)
                        if attempt == max_retries - 1:
                            failed += 1
                    else:
                        log_warning(logger, f"Failed to fetch avatar for {hibob_id}", e)
                        failed += 1
                        break

        logger.info(f"Avatar sync complete: {downloaded} downloaded, {skipped} skipped, {failed} failed, {rate_limited} rate limited")
        return {
            "downloaded": downloaded,
            "skipped": skipped,
            "failed": failed,
            "rate_limited": rate_limited,
        }

    async def _sync_license_provider(
        self,
        provider,
        provider_id: UUID,
    ) -> dict[str, Any]:
        """Sync licenses from a provider.

        Uses multi-level matching to assign licenses to employees:
        1. Exact email match (company emails only)
        2. Local part match (suggests matches for review)
        3. Fuzzy name match (suggests matches for review)

        GDPR: No private emails are stored. External matches are only suggested.

        Args:
            provider: Provider instance
            provider_id: Provider UUID

        Returns:
            Dict with sync results
        """
        licenses = await provider.fetch_licenses()
        synced_at = datetime.now(timezone.utc)
        created = 0
        updated = 0

        # Get provider config for pricing
        provider_orm = await self.provider_repo.get_by_id(provider_id)
        provider_config = provider_orm.config or {} if provider_orm else {}
        pricing_config = provider_config.get("license_pricing", {})
        package_pricing = provider_config.get("package_pricing")

        # Calculate package pricing (cost per license = total / package_size)
        # Use max_users from provider_license_info (package size) for consistent pricing
        package_monthly_cost: Decimal | None = None
        package_currency = "EUR"
        if package_pricing:
            total_cost = Decimal(str(package_pricing.get("cost", "0")))
            billing_cycle = package_pricing.get("billing_cycle", "yearly")
            package_currency = package_pricing.get("currency", "EUR")

            # Get package size from provider_license_info (max_users)
            # This ensures cost per license matches the provider pricing page display
            provider_license_info = provider_config.get("provider_license_info", {})
            package_size = provider_license_info.get("max_users", 0)

            # Convert to monthly cost
            if billing_cycle == "yearly":
                monthly_total = total_cost / 12
            elif billing_cycle == "monthly":
                monthly_total = total_cost
            else:
                monthly_total = Decimal("0")

            # Divide by package size to get cost per license
            # This gives "cost per entitled seat" which is consistent with the provider pricing page
            if monthly_total > 0 and package_size > 0:
                package_monthly_cost = monthly_total / package_size
                logger.info(
                    f"Package pricing: {total_cost} {package_currency}/{billing_cycle} "
                    f"/ {package_size} package seats = {package_monthly_cost:.2f}/month per license"
                )
            elif monthly_total > 0:
                # Fallback: if no max_users configured, log warning
                logger.warning(
                    f"Package pricing configured but no max_users in provider_license_info. "
                    f"Cannot calculate per-license cost."
                )

        # Get company domains for matching
        settings_repo = SettingsRepository(self.session)
        domains_setting = await settings_repo.get("company_domains")
        company_domains = domains_setting.get("domains", []) if domains_setting else []

        # Initialize matching service
        matching_service = MatchingService(self.session)

        # Track licenses for batch matching
        new_licenses: list[tuple[dict, Any]] = []

        for lic_data in licenses:
            existing = await self.license_repo.get_by_provider_and_external_id(
                provider_id,
                lic_data["external_user_id"],
            )

            # Apply pricing: package pricing takes precedence, then per-type pricing
            monthly_cost = lic_data.get("monthly_cost")
            currency = lic_data.get("currency", "EUR")
            license_type = lic_data.get("license_type")

            if package_monthly_cost is not None:
                # Package pricing: same cost for all licenses
                monthly_cost = package_monthly_cost
                currency = package_currency
            elif license_type and license_type in pricing_config:
                price_info = pricing_config[license_type]
                cost = Decimal(price_info.get("cost", "0"))
                billing_cycle = price_info.get("billing_cycle", "yearly")
                currency = price_info.get("currency", "EUR")

                # Calculate monthly equivalent
                if billing_cycle == "yearly":
                    monthly_cost = cost / 12
                elif billing_cycle == "monthly":
                    monthly_cost = cost
                else:
                    # perpetual/one_time - no recurring monthly cost
                    monthly_cost = Decimal("0")

            # Use matching service for employee assignment
            # Use email field if available (e.g., JetBrains provides email separately from license ID)
            # Fall back to external_user_id (which is typically an email for most providers)
            match_identifier = lic_data.get("email") or lic_data["external_user_id"]
            match_result = await matching_service.match_license(
                match_identifier,
                company_domains,
            )

            # Determine employee_id and match fields
            employee_id = None
            suggested_employee_id = None
            match_confidence = match_result.confidence if match_result.confidence > 0 else None
            match_method = match_result.method
            match_status = match_result.status

            if match_result.should_auto_assign:
                employee_id = match_result.employee_id
            elif match_result.should_suggest:
                suggested_employee_id = match_result.employee_id

            # Check for global service account patterns
            svc_pattern = await self.svc_account_pattern_repo.matches_email(
                lic_data["external_user_id"]
            )
            is_service_account = svc_pattern is not None
            service_account_name = svc_pattern.name if svc_pattern else None
            service_account_owner_id = svc_pattern.owner_id if svc_pattern else None

            # Check for global admin account patterns (only if not a service account)
            admin_pattern = None
            is_admin_account = False
            admin_account_name = None
            admin_account_owner_id = None
            if not is_service_account:
                admin_pattern = await self.admin_account_pattern_repo.matches_email(
                    lic_data["external_user_id"]
                )
                is_admin_account = admin_pattern is not None
                admin_account_name = admin_pattern.name if admin_pattern else None
                admin_account_owner_id = admin_pattern.owner_id if admin_pattern else None

            license_orm = await self.license_repo.upsert(
                provider_id=provider_id,
                external_user_id=lic_data["external_user_id"],
                employee_id=employee_id if not is_service_account else None,
                license_type=license_type,
                status=lic_data.get("status", "active"),
                assigned_at=lic_data.get("assigned_at"),
                last_activity_at=lic_data.get("last_activity_at"),
                monthly_cost=monthly_cost,
                currency=currency,
                metadata=lic_data.get("metadata"),
                synced_at=synced_at,
            )

            # Update service account fields if pattern matched
            if is_service_account:
                license_orm.is_service_account = True
                license_orm.service_account_name = service_account_name
                license_orm.service_account_owner_id = service_account_owner_id
                # Clear match fields for service accounts
                license_orm.suggested_employee_id = None
                license_orm.match_confidence = None
                license_orm.match_method = None
                license_orm.match_status = None
            elif is_admin_account:
                # Admin accounts are personal, so they keep the employee link if matched
                license_orm.is_admin_account = True
                license_orm.admin_account_name = admin_account_name
                license_orm.admin_account_owner_id = admin_account_owner_id
                # Update match fields normally
                license_orm.suggested_employee_id = suggested_employee_id
                license_orm.match_confidence = match_confidence
                license_orm.match_method = match_method
                license_orm.match_status = match_status
            else:
                # Update match fields
                license_orm.suggested_employee_id = suggested_employee_id
                license_orm.match_confidence = match_confidence
                license_orm.match_method = match_method
                license_orm.match_status = match_status

            if existing:
                updated += 1
            else:
                created += 1

        await self.session.flush()

        # Store provider metadata (e.g., license info) if available
        if hasattr(provider, "get_provider_metadata"):
            metadata = provider.get_provider_metadata()
            if metadata:
                provider_orm = await self.provider_repo.get_by_id(provider_id)
                if provider_orm:
                    config = provider_orm.config or {}
                    config["provider_license_info"] = metadata
                    await self.provider_repo.update(provider_id, config=config)

        return {
            "provider": provider.__class__.__name__,
            "licenses_created": created,
            "licenses_updated": updated,
            "total": len(licenses),
        }

    async def trigger_sync(self, provider_id: UUID | None = None) -> dict[str, Any]:
        """Trigger a sync operation.

        Args:
            provider_id: Specific provider to sync, or None for all

        Returns:
            Dict with sync results
        """
        if provider_id:
            return await self.sync_provider(provider_id)
        return await self.sync_all_providers()

    async def resync_avatars(self, force: bool = False) -> dict[str, Any]:
        """Resync all employee avatars from HiBob.

        Args:
            force: If True, delete existing avatars and re-download all

        Returns:
            Dict with sync results
        """
        from licence_api.providers.hibob import HiBobProvider

        # Get HiBob provider
        hibob_provider = await self.provider_repo.get_by_name(ProviderName.HIBOB)
        if hibob_provider is None:
            raise ValueError("HiBob provider not configured")

        # If force, delete all existing avatars
        if force and AVATAR_DIR.exists():
            for avatar_file in AVATAR_DIR.glob("*.jpg"):
                avatar_file.unlink()
            logger.info("Deleted all existing avatars for forced resync")

        # Get credentials and create provider
        credentials = self.encryption.decrypt(hibob_provider.credentials_encrypted)
        provider = HiBobProvider(credentials)

        # Get all employees from database
        employees = await self.employee_repo.get_all()
        employee_data = [{"hibob_id": emp.hibob_id} for emp in employees if emp.hibob_id]

        # Sync avatars
        result = await self._sync_avatars(provider, employee_data)

        return {
            "provider": "hibob",
            "avatars": result,
        }
