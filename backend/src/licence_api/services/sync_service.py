"""Sync service for orchestrating provider synchronization.

Architecture Note (MVC-06):
    Audit logging and cache invalidation are handled within this service layer
    (not in routers) to enforce strict MVC separation.
"""

import asyncio
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import AVATAR_DIR
from licence_api.middleware.error_handler import sanitize_error_for_audit
from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.domain.provider import ProviderName, SyncStatus
from licence_api.repositories.admin_account_pattern_repository import AdminAccountPatternRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.service_account_license_type_repository import (
    ServiceAccountLicenseTypeRepository,
)
from licence_api.repositories.service_account_pattern_repository import (
    ServiceAccountPatternRepository,
)
from licence_api.repositories.settings_repository import SettingsRepository
from licence_api.security.encryption import get_encryption_service
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.cache_service import get_cache_service
from licence_api.services.matching_service import MatchingService
from licence_api.utils.pattern_matcher import PatternMatcher
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
        self.svc_account_license_type_repo = ServiceAccountLicenseTypeRepository(session)
        self.admin_account_pattern_repo = AdminAccountPatternRepository(session)
        self.encryption = get_encryption_service()
        self.audit_service = AuditService(session)

    def _update_match_fields_if_better(
        self,
        license_orm: Any,
        suggested_employee_id: UUID | None,
        match_confidence: float | None,
        match_method: str | None,
        match_status: str | None,
    ) -> None:
        """Update match fields only if the new match is better than existing.

        Preserves existing suggestions if:
        - The user has manually reviewed the match (match_reviewed_at is set)
        - The existing confidence is higher than the new one
        - There's an existing suggestion but no new one

        Args:
            license_orm: The license ORM object to update
            suggested_employee_id: New suggested employee ID
            match_confidence: New match confidence
            match_method: New match method
            match_status: New match status
        """
        # If user has manually reviewed this match, don't overwrite
        if license_orm.match_reviewed_at is not None:
            return

        # If there's no new suggestion
        if suggested_employee_id is None:
            # Keep existing suggestion if present, but update confidence/status
            # to reflect that we tried to match again
            if license_orm.suggested_employee_id is None:
                # No existing suggestion either, update all fields
                license_orm.match_confidence = match_confidence
                license_orm.match_method = match_method
                license_orm.match_status = match_status
            # else: keep existing suggestion unchanged
            return

        # There's a new suggestion - check if it's better than existing
        existing_confidence = license_orm.match_confidence or 0.0
        new_confidence = match_confidence or 0.0

        # Update if: no existing suggestion, or new confidence is higher
        if license_orm.suggested_employee_id is None or new_confidence > existing_confidence:
            license_orm.suggested_employee_id = suggested_employee_id
            license_orm.match_confidence = match_confidence
            license_orm.match_method = match_method
            license_orm.match_status = match_status

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
                    datetime.now(UTC),
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
                result = await self._sync_hibob(provider_impl)
            elif provider.name == ProviderName.PERSONIO:
                result = await self._sync_personio(provider_impl)
            else:
                result = await self._sync_license_provider(provider_impl, provider_id)

            # Update status to success
            await self.provider_repo.update_sync_status(
                provider_id,
                SyncStatus.SUCCESS,
                datetime.now(UTC),
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
            HuggingFaceProvider,
            JetBrainsProvider,
            MailjetProvider,
            MattermostProvider,
            MicrosoftProvider,
            MiroProvider,
            OnePasswordProvider,
            OpenAIProvider,
            PersonioProvider,
            SlackProvider,
            ZoomProvider,
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
            ProviderName.HUGGINGFACE: HuggingFaceProvider,
            ProviderName.JETBRAINS: JetBrainsProvider,
            ProviderName.MAILJET: MailjetProvider,
            ProviderName.MATTERMOST: MattermostProvider,
            ProviderName.MICROSOFT: MicrosoftProvider,
            ProviderName.MIRO: MiroProvider,
            ProviderName.ONEPASSWORD: OnePasswordProvider,
            ProviderName.OPENAI: OpenAIProvider,
            ProviderName.PERSONIO: PersonioProvider,
            ProviderName.SLACK: SlackProvider,
            ProviderName.ZOOM: ZoomProvider,
        }

        provider_class = providers.get(name)
        if provider_class is None:
            raise ValueError(f"Unknown provider: {name}")

        return provider_class(credentials)

    async def _sync_hris_employees(
        self,
        provider,
        provider_name: str,
        sync_avatars: bool = False,
    ) -> dict[str, Any]:
        """Sync employees from HRIS provider (HiBob or Personio).

        Uses batch loading to avoid N+1 queries when checking for existing employees.

        Args:
            provider: HRIS provider instance
            provider_name: Name for result dict (e.g., "hibob", "personio")
            sync_avatars: Whether to sync avatars after employee data

        Returns:
            Dict with sync results
        """
        employees = await provider.fetch_employees()
        synced_at = datetime.now(UTC)
        created = 0
        updated = 0

        # Batch load all existing employees by hibob_id to avoid N+1 queries
        hibob_ids = [emp_data["hibob_id"] for emp_data in employees]
        existing_employees = await self.employee_repo.get_by_hibob_ids(hibob_ids)

        for emp_data in employees:
            existing = existing_employees.get(emp_data["hibob_id"])
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

        result: dict[str, Any] = {
            "provider": provider_name,
            "employees_created": created,
            "employees_updated": updated,
            "total": len(employees),
            "managers_resolved": managers_resolved,
        }

        # Sync avatars after employee data (HiBob only)
        if sync_avatars:
            avatar_result = await self._sync_avatars(provider, employees)
            result["avatars"] = avatar_result

        return result

    async def _sync_hibob(self, provider) -> dict[str, Any]:
        """Sync employees from HiBob.

        Args:
            provider: HiBob provider instance

        Returns:
            Dict with sync results
        """
        return await self._sync_hris_employees(provider, "hibob", sync_avatars=True)

    async def _sync_personio(self, provider) -> dict[str, Any]:
        """Sync employees from Personio.

        Args:
            provider: Personio provider instance

        Returns:
            Dict with sync results
        """
        return await self._sync_hris_employees(provider, "personio", sync_avatars=False)

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
                            logger.info(
                                f"Avatar progress: {downloaded} downloaded, {skipped} skipped"
                            )
                    else:
                        # Could be 429 or no avatar - check if we should retry
                        failed += 1
                    break  # Success or definite failure, exit retry loop

                except Exception as e:
                    error_msg = str(e).lower()
                    if "429" in error_msg or "too many" in error_msg:
                        rate_limited += 1
                        backoff = base_delay * (2**attempt) * 10  # Exponential backoff
                        logger.warning(
                            f"Rate limited for {hibob_id}, waiting {backoff}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(backoff)
                        if attempt == max_retries - 1:
                            failed += 1
                    else:
                        log_warning(logger, f"Failed to fetch avatar for {hibob_id}", e)
                        failed += 1
                        break

        logger.info(
            f"Avatar sync complete: {downloaded} downloaded, {skipped} skipped, "
            f"{failed} failed, {rate_limited} rate limited"
        )
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
        synced_at = datetime.now(UTC)
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
            elif billing_cycle == "quarterly":
                monthly_total = total_cost / 3
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
                    "Package pricing configured but no max_users in provider_license_info. "
                    "Cannot calculate per-license cost."
                )

        # Get company domains for matching
        settings_repo = SettingsRepository(self.session)
        domains_setting = await settings_repo.get("company_domains")
        company_domains = domains_setting.get("domains", []) if domains_setting else []

        # Initialize matching service
        matching_service = MatchingService(self.session)

        # Load all patterns once for optimized bulk matching (avoids N+1 queries)
        svc_patterns = await self.svc_account_pattern_repo.get_all()
        admin_patterns = await self.admin_account_pattern_repo.get_all()
        svc_license_types = await self.svc_account_license_type_repo.get_all()
        pattern_matcher = PatternMatcher(svc_patterns, admin_patterns, svc_license_types)

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
                elif billing_cycle == "quarterly":
                    monthly_cost = cost / 3
                elif billing_cycle == "monthly":
                    monthly_cost = cost
                else:
                    # perpetual/one_time - no recurring monthly cost
                    monthly_cost = Decimal("0")

            # Use matching service for employee assignment
            # Use email field if available (JetBrains provides email separately from license ID)
            # Fall back to external_user_id (typically an email for most providers)
            match_identifier = lic_data.get("email") or lic_data["external_user_id"]

            # Get username and display name from metadata for matching
            # This enables matching by linked external accounts (e.g., HuggingFace username)
            # and fuzzy name matching by display name (e.g., HuggingFace fullName)
            metadata = lic_data.get("metadata", {})
            username_for_matching = metadata.get("username") or metadata.get("hf_username")
            display_name_for_matching = (
                metadata.get("fullName")
                or metadata.get("fullname")
                or metadata.get("display_name")
                or metadata.get("displayName")
            )

            match_result = await matching_service.match_license(
                match_identifier,
                company_domains,
                provider_type=provider_orm.name if provider_orm else None,
                username=username_for_matching,
                display_name=display_name_for_matching,
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

            # Check for global service account patterns (email-based) using preloaded patterns
            svc_match = pattern_matcher.match_service_account_email(lic_data["external_user_id"])
            is_service_account = svc_match.matched
            service_account_name = svc_match.name
            service_account_owner_id = svc_match.owner_id

            # Check for license type-based service account rules if not already matched
            if not is_service_account and license_type:
                svc_type_match = pattern_matcher.match_service_account_license_type(license_type)
                if svc_type_match.matched:
                    is_service_account = True
                    service_account_name = svc_type_match.name
                    service_account_owner_id = svc_type_match.owner_id

            # Check for global admin account patterns (only if not a service account)
            is_admin_account = False
            admin_account_name = None
            admin_account_owner_id = None
            if not is_service_account:
                admin_match = pattern_matcher.match_admin_account_email(
                    lic_data["external_user_id"]
                )
                is_admin_account = admin_match.matched
                admin_account_name = admin_match.name
                admin_account_owner_id = admin_match.owner_id

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
                # Update match fields, preserving existing suggestions
                self._update_match_fields_if_better(
                    license_orm, suggested_employee_id, match_confidence, match_method, match_status
                )
            else:
                # Update match fields, preserving existing suggestions
                self._update_match_fields_if_better(
                    license_orm, suggested_employee_id, match_confidence, match_method, match_status
                )

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

    async def trigger_sync(
        self,
        provider_id: UUID | None = None,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Trigger a sync operation with audit logging and cache invalidation.

        Args:
            provider_id: Specific provider to sync, or None for all
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            Dict with sync results

        Raises:
            ConnectionError: On network errors
            TimeoutError: On timeout
            OSError: On OS-level errors
            ValueError: On invalid provider
        """
        try:
            if provider_id:
                results = await self.sync_provider(provider_id)
            else:
                results = await self.sync_all_providers()

            # Audit log success
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={
                        "results": results,
                        "scope": "single" if provider_id else "all",
                    },
                )

            # Invalidate caches after sync (data has changed)
            cache = await get_cache_service()
            await cache.invalidate_all()

            return results

        except (ConnectionError, TimeoutError, OSError) as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={
                        "success": False,
                        "error_code": "CONNECTION_ERROR",
                        "error_type": type(e).__name__,
                    },
                )
            raise
        except ValueError:
            raise
        except Exception as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={
                        "success": False,
                        **sanitize_error_for_audit(e),
                    },
                )
            raise

    async def trigger_provider_sync(
        self,
        provider_id: UUID,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Sync a specific provider with audit logging and cache invalidation.

        Args:
            provider_id: Provider UUID to sync
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            Dict with sync results

        Raises:
            ValueError: If provider not found
            ConnectionError: On network errors
            TimeoutError: On timeout
            OSError: On OS-level errors
        """
        try:
            results = await self.sync_provider(provider_id)

            # Audit log success
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={"results": results},
                )

            # Invalidate caches after sync (data has changed)
            cache = await get_cache_service()
            await cache.invalidate_all()

            return results

        except ValueError:
            raise
        except (ConnectionError, TimeoutError, OSError) as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={
                        "success": False,
                        "error_code": "CONNECTION_ERROR",
                        "error_type": type(e).__name__,
                    },
                )
            raise
        except Exception as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=provider_id,
                    user=user,
                    request=request,
                    details={
                        "success": False,
                        **sanitize_error_for_audit(e),
                    },
                )
            raise

    async def resync_avatars(
        self,
        force: bool = False,
        user: AdminUser | None = None,
        request: Request | None = None,
    ) -> dict[str, Any]:
        """Resync all employee avatars from HiBob.

        Args:
            force: If True, delete existing avatars and re-download all
            user: AdminUser for audit logging
            request: HTTP request for audit logging

        Returns:
            Dict with sync results

        Raises:
            ValueError: If HiBob provider not configured
            ConnectionError: On network errors
            TimeoutError: On timeout
            OSError: On OS-level errors
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

        try:
            # Get credentials and create provider
            credentials = self.encryption.decrypt(hibob_provider.credentials_encrypted)
            provider = HiBobProvider(credentials)

            # Get all employees from database
            employees = await self.employee_repo.get_all()
            employee_data = [{"hibob_id": emp.hibob_id} for emp in employees if emp.hibob_id]

            # Sync avatars
            result = await self._sync_avatars(provider, employee_data)

            results = {
                "provider": "hibob",
                "avatars": result,
            }

            # Audit log success
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=None,
                    user=user,
                    request=request,
                    details={
                        "action": "avatar_resync",
                        "force": force,
                        "results": results,
                    },
                )

            return results

        except (ConnectionError, TimeoutError, OSError) as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=None,
                    user=user,
                    request=request,
                    details={
                        "action": "avatar_resync",
                        "success": False,
                        "error_code": "CONNECTION_ERROR",
                        "error_type": type(e).__name__,
                    },
                )
            raise
        except Exception as e:
            if user:
                await self.audit_service.log(
                    action=AuditAction.PROVIDER_SYNC,
                    resource_type=ResourceType.PROVIDER,
                    resource_id=None,
                    user=user,
                    request=request,
                    details={
                        "action": "avatar_resync",
                        "success": False,
                        **sanitize_error_for_audit(e),
                    },
                )
            raise
