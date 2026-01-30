"""Sync service for orchestrating provider synchronization."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.provider import ProviderName, SyncStatus
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.security.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Avatar storage directory
AVATAR_DIR = Path(__file__).parent.parent.parent.parent / "data" / "avatars"


class SyncService:
    """Service for synchronizing data from providers."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.provider_repo = ProviderRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.license_repo = LicenseRepository(session)
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
                logger.error(f"Error syncing provider {provider.name}: {e}")
                results[provider.name] = {"error": str(e)}
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
            logger.error(f"Error syncing provider {provider.name}: {e}")
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
            CursorProvider,
            FigmaProvider,
            GitHubProvider,
            GitLabProvider,
            GoogleWorkspaceProvider,
            HiBobProvider,
            JetBrainsProvider,
            MattermostProvider,
            MicrosoftProvider,
            MiroProvider,
            OnePasswordProvider,
            OpenAIProvider,
            SlackProvider,
        )

        providers = {
            ProviderName.CURSOR: CursorProvider,
            ProviderName.FIGMA: FigmaProvider,
            ProviderName.GITHUB: GitHubProvider,
            ProviderName.GITLAB: GitLabProvider,
            ProviderName.GOOGLE_WORKSPACE: GoogleWorkspaceProvider,
            ProviderName.HIBOB: HiBobProvider,
            ProviderName.JETBRAINS: JetBrainsProvider,
            ProviderName.MATTERMOST: MattermostProvider,
            ProviderName.MICROSOFT: MicrosoftProvider,
            ProviderName.MIRO: MiroProvider,
            ProviderName.ONEPASSWORD: OnePasswordProvider,
            ProviderName.OPENAI: OpenAIProvider,
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
            )
            if existing:
                updated += 1
            else:
                created += 1

        # Sync avatars after employee data
        avatar_result = await self._sync_avatars(provider, employees)

        return {
            "provider": "hibob",
            "employees_created": created,
            "employees_updated": updated,
            "total": len(employees),
            "avatars": avatar_result,
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
                        logger.warning(f"Failed to fetch avatar for {hibob_id}: {e}")
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

        Args:
            provider: Provider instance
            provider_id: Provider UUID

        Returns:
            Dict with sync results
        """
        from decimal import Decimal

        licenses = await provider.fetch_licenses()
        synced_at = datetime.now(timezone.utc)
        created = 0
        updated = 0

        # Get provider config for pricing
        provider_orm = await self.provider_repo.get_by_id(provider_id)
        pricing_config = (provider_orm.config or {}).get("license_pricing", {}) if provider_orm else {}

        for lic_data in licenses:
            # Try to match with employee by email
            employee_id = None
            if "email" in lic_data:
                employee = await self.employee_repo.get_by_email(lic_data["email"])
                if employee:
                    employee_id = employee.id

            existing = await self.license_repo.get_by_provider_and_external_id(
                provider_id,
                lic_data["external_user_id"],
            )

            # Apply pricing from config if available
            monthly_cost = lic_data.get("monthly_cost")
            currency = lic_data.get("currency", "EUR")
            license_type = lic_data.get("license_type")

            if license_type and license_type in pricing_config:
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

            await self.license_repo.upsert(
                provider_id=provider_id,
                external_user_id=lic_data["external_user_id"],
                employee_id=employee_id,
                license_type=license_type,
                status=lic_data.get("status", "active"),
                assigned_at=lic_data.get("assigned_at"),
                last_activity_at=lic_data.get("last_activity_at"),
                monthly_cost=monthly_cost,
                currency=currency,
                metadata=lic_data.get("metadata"),
                synced_at=synced_at,
            )

            if existing:
                updated += 1
            else:
                created += 1

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
