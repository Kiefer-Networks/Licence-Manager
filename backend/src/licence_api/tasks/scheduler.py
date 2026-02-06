"""Background task scheduler using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from licence_api.config import get_settings

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


async def sync_all_providers_job() -> None:
    """Background job to sync all providers."""
    from licence_api.database import async_session_maker
    from licence_api.services.sync_service import SyncService

    logger.info("Starting scheduled sync of all providers")

    async with async_session_maker() as session:
        try:
            service = SyncService(session)
            results = await service.sync_all_providers()
            await session.commit()
            logger.info(f"Scheduled sync completed: {results}")
        except Exception as e:
            logger.error(f"Scheduled sync failed: {e}")
            await session.rollback()


async def check_inactive_licenses_job() -> None:
    """Background job to check for inactive licenses and send notifications."""
    from licence_api.database import async_session_maker
    from licence_api.repositories.settings_repository import SettingsRepository
    from licence_api.services.notification_service import NotificationService
    from licence_api.services.report_service import ReportService

    logger.info("Checking for inactive licenses")

    async with async_session_maker() as session:
        try:
            report_service = ReportService(session)
            notification_service = NotificationService(session)
            settings_repo = SettingsRepository(session)

            # Get inactive license report
            report = await report_service.get_inactive_license_report(days_threshold=30)

            if report.total_inactive > 0:
                # Get Slack token from settings
                slack_config = await settings_repo.get("slack_config")
                if slack_config and slack_config.get("bot_token"):
                    for entry in report.licenses[:10]:  # Limit notifications
                        await notification_service.notify_inactive_license(
                            provider_name=entry.provider_name,
                            user_email=entry.employee_email or entry.external_user_id,
                            days_inactive=entry.days_inactive,
                            slack_token=slack_config["bot_token"],
                        )

            await session.commit()
            logger.info(f"Inactive license check completed: {report.total_inactive} found")
        except Exception as e:
            logger.error(f"Inactive license check failed: {e}")
            await session.rollback()


async def check_offboarded_employees_job() -> None:
    """Background job to check for offboarded employees with licenses."""
    from licence_api.database import async_session_maker
    from licence_api.repositories.settings_repository import SettingsRepository
    from licence_api.services.notification_service import NotificationService
    from licence_api.services.report_service import ReportService

    logger.info("Checking for offboarded employees with licenses")

    async with async_session_maker() as session:
        try:
            report_service = ReportService(session)
            notification_service = NotificationService(session)
            settings_repo = SettingsRepository(session)

            # Get offboarding report
            report = await report_service.get_offboarding_report()

            if report.total_offboarded_with_licenses > 0:
                # Get Slack token from settings
                slack_config = await settings_repo.get("slack_config")
                if slack_config and slack_config.get("bot_token"):
                    for employee in report.employees[:5]:  # Limit notifications
                        await notification_service.notify_employee_offboarded(
                            employee_name=employee.employee_name,
                            employee_email=employee.employee_email,
                            pending_licenses=employee.pending_licenses,
                            slack_token=slack_config["bot_token"],
                        )

            await session.commit()
            logger.info(
                f"Offboarding check completed: {report.total_offboarded_with_licenses} found"
            )
        except Exception as e:
            logger.error(f"Offboarding check failed: {e}")
            await session.rollback()


async def check_expiring_licenses_job() -> None:
    """Background job to check for expiring licenses, packages, and org licenses."""
    from licence_api.database import async_session_maker
    from licence_api.repositories.settings_repository import SettingsRepository
    from licence_api.services.expiration_service import ExpirationService
    from licence_api.services.notification_service import NotificationService

    logger.info("Checking for expiring and expired licenses, packages, and org licenses")

    async with async_session_maker() as session:
        try:
            expiration_service = ExpirationService(session)
            notification_service = NotificationService(session)
            settings_repo = SettingsRepository(session)

            # First, update any licenses that have expired or have effective cancellation dates
            update_counts = await expiration_service.check_and_update_expired_licenses()
            logger.info(f"Updated expired/cancelled items: {update_counts}")

            # Get Slack token from settings (needed for notifications)
            slack_config = await settings_repo.get("slack_config")
            slack_token = slack_config.get("bot_token") if slack_config else None

            # Send notifications for items that just expired/cancelled
            if slack_token:
                if update_counts.get("licenses_expired", 0) > 0:
                    await notification_service.notify_license_expired(
                        provider_name="Multiple providers",
                        license_type=None,
                        user_email="Multiple users",
                        expired_count=update_counts["licenses_expired"],
                        slack_token=slack_token,
                    )
                if update_counts.get("packages_expired", 0) > 0:
                    await notification_service.notify_package_expired(
                        provider_name="Multiple providers",
                        package_name="Multiple packages",
                        seat_count=update_counts["packages_expired"],
                        slack_token=slack_token,
                    )
                if update_counts.get("org_licenses_expired", 0) > 0:
                    count = update_counts["org_licenses_expired"]
                    await notification_service.notify_org_license_expired(
                        provider_name="Multiple providers",
                        org_license_name=f"{count} organization license(s)",
                        slack_token=slack_token,
                    )

            # Get threshold settings
            thresholds = await settings_repo.get("thresholds")
            expiring_days = thresholds.get("expiring_days", 30) if thresholds else 30

            total_expiring = 0

            # Check expiring individual licenses
            expiring_licenses = await expiration_service.get_expiring_licenses(
                days_ahead=expiring_days
            )
            if expiring_licenses and slack_token:
                from collections import defaultdict

                by_provider: dict = defaultdict(list)
                for lic, provider, employee in expiring_licenses:
                    by_provider[provider.display_name].append(lic)

                for provider_name, licenses in by_provider.items():
                    if licenses:
                        min_days = min(
                            (lic.expires_at - datetime.now().date()).days
                            for lic in licenses
                            if lic.expires_at
                        )
                        await notification_service.notify_license_expiring(
                            provider_name=provider_name,
                            license_type=licenses[0].license_type,
                            days_until_expiry=min_days,
                            affected_count=len(licenses),
                            slack_token=slack_token,
                        )
            total_expiring += len(expiring_licenses)

            # Check expiring packages
            expiring_packages = await expiration_service.get_expiring_packages(
                days_ahead=expiring_days
            )
            if expiring_packages and slack_token:
                from collections import defaultdict

                by_provider_pkg: dict = defaultdict(list)
                for pkg in expiring_packages:
                    by_provider_pkg[pkg.provider.display_name].append(pkg)

                for provider_name, packages in by_provider_pkg.items():
                    if packages:
                        min_days = min(
                            (pkg.contract_end - datetime.now().date()).days
                            for pkg in packages
                            if pkg.contract_end
                        )
                        await notification_service.notify_license_expiring(
                            provider_name=f"{provider_name} (Package)",
                            license_type=packages[0].license_type,
                            days_until_expiry=min_days,
                            affected_count=len(packages),
                            slack_token=slack_token,
                        )
            total_expiring += len(expiring_packages)

            # Check expiring org licenses
            expiring_org = await expiration_service.get_expiring_org_licenses(
                days_ahead=expiring_days
            )
            if expiring_org and slack_token:
                from collections import defaultdict

                by_provider_org: dict = defaultdict(list)
                for org_lic in expiring_org:
                    by_provider_org[org_lic.provider.display_name].append(org_lic)

                for provider_name, org_licenses in by_provider_org.items():
                    if org_licenses:
                        min_days = min(
                            (ol.expires_at - datetime.now().date()).days
                            for ol in org_licenses
                            if ol.expires_at
                        )
                        await notification_service.notify_license_expiring(
                            provider_name=f"{provider_name} (Org License)",
                            license_type=org_licenses[0].name,
                            days_until_expiry=min_days,
                            affected_count=len(org_licenses),
                            slack_token=slack_token,
                        )
            total_expiring += len(expiring_org)

            await session.commit()
            logger.info(
                f"Expiring check completed: {len(expiring_licenses)} licenses, "
                f"{len(expiring_packages)} packages, {len(expiring_org)} org licenses"
            )
        except Exception as e:
            logger.error(f"Expiring licenses check failed: {e}")
            await session.rollback()


async def start_scheduler() -> None:
    """Start the background task scheduler."""
    global _scheduler

    settings = get_settings()
    _scheduler = AsyncIOScheduler()

    # Schedule provider sync
    _scheduler.add_job(
        sync_all_providers_job,
        trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
        id="sync_all_providers",
        name="Sync all providers",
        replace_existing=True,
        next_run_time=datetime.now(),  # Run immediately on startup
    )

    # Schedule inactive license check (daily)
    _scheduler.add_job(
        check_inactive_licenses_job,
        trigger=IntervalTrigger(hours=24),
        id="check_inactive_licenses",
        name="Check inactive licenses",
        replace_existing=True,
    )

    # Schedule offboarding check (every 6 hours)
    _scheduler.add_job(
        check_offboarded_employees_job,
        trigger=IntervalTrigger(hours=6),
        id="check_offboarded_employees",
        name="Check offboarded employees",
        replace_existing=True,
    )

    # Schedule expiring licenses check (daily)
    _scheduler.add_job(
        check_expiring_licenses_job,
        trigger=IntervalTrigger(hours=24),
        id="check_expiring_licenses",
        name="Check expiring licenses",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Background scheduler started")

    # Initialize backup schedule from configuration
    await initialize_backup_schedule()


async def stop_scheduler() -> None:
    """Stop the background task scheduler."""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Background scheduler stopped")


# =============================================================================
# Scheduled Backup Job
# =============================================================================


async def scheduled_backup_job() -> None:
    """Background job to create scheduled backups."""
    from licence_api.database import async_session_maker
    from licence_api.services.backup_service import BackupService

    logger.info("Starting scheduled backup")

    async with async_session_maker() as session:
        try:
            service = BackupService(session)
            result = await service.create_scheduled_backup()
            if result:
                logger.info(f"Scheduled backup completed: {result.filename}")
            else:
                logger.debug("Scheduled backup skipped (not configured)")
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")


async def update_backup_schedule(enabled: bool, cron_expression: str) -> None:
    """Update or create the backup schedule dynamically.

    Args:
        enabled: Whether backups are enabled
        cron_expression: Cron expression for schedule
    """
    global _scheduler

    if not _scheduler:
        logger.warning("Cannot update backup schedule: scheduler not running")
        return

    job_id = "scheduled_backup"

    # Remove existing job if present
    existing_job = _scheduler.get_job(job_id)
    if existing_job:
        _scheduler.remove_job(job_id)
        logger.debug("Removed existing backup schedule")

    if enabled:
        try:
            _scheduler.add_job(
                scheduled_backup_job,
                trigger=CronTrigger.from_crontab(cron_expression),
                id=job_id,
                name="Scheduled backup",
                replace_existing=True,
            )
            logger.info(f"Backup schedule updated: {cron_expression}")
        except ValueError as e:
            logger.error(f"Invalid cron expression '{cron_expression}': {e}")
    else:
        logger.info("Backup schedule disabled")


async def initialize_backup_schedule() -> None:
    """Initialize backup schedule from stored configuration."""
    from licence_api.database import async_session_maker
    from licence_api.services.backup_service import BackupService

    async with async_session_maker() as session:
        try:
            service = BackupService(session)
            config = await service.get_config()
            if config.enabled:
                await update_backup_schedule(True, config.schedule)
        except Exception as e:
            logger.warning(f"Failed to initialize backup schedule: {e}")
