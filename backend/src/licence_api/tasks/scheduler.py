"""Background task scheduler using APScheduler."""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
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
    from licence_api.services.report_service import ReportService
    from licence_api.services.notification_service import NotificationService
    from licence_api.repositories.settings_repository import SettingsRepository

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
    from licence_api.services.report_service import ReportService
    from licence_api.services.notification_service import NotificationService
    from licence_api.repositories.settings_repository import SettingsRepository

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
    """Background job to check for expiring licenses and update expired ones."""
    from licence_api.database import async_session_maker
    from licence_api.services.expiration_service import ExpirationService
    from licence_api.services.notification_service import NotificationService
    from licence_api.repositories.settings_repository import SettingsRepository

    logger.info("Checking for expiring and expired licenses")

    async with async_session_maker() as session:
        try:
            expiration_service = ExpirationService(session)
            notification_service = NotificationService(session)
            settings_repo = SettingsRepository(session)

            # First, update any licenses that have expired or have effective cancellation dates
            update_counts = await expiration_service.check_and_update_expired_licenses()
            logger.info(f"Updated expired/cancelled licenses: {update_counts}")

            # Get threshold settings
            thresholds = await settings_repo.get("thresholds")
            expiring_days = thresholds.get("expiring_days", 30) if thresholds else 30

            # Get expiring licenses for notification
            expiring = await expiration_service.get_expiring_licenses(days_ahead=expiring_days)

            if expiring:
                # Get Slack token from settings
                slack_config = await settings_repo.get("slack_config")
                if slack_config and slack_config.get("bot_token"):
                    # Group by provider for notifications
                    from collections import defaultdict
                    by_provider: dict = defaultdict(list)
                    for lic, provider, employee in expiring:
                        by_provider[provider.display_name].append(lic)

                    for provider_name, licenses in by_provider.items():
                        if licenses:
                            # Get min days until expiry for this provider
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
                                slack_token=slack_config["bot_token"],
                            )

            await session.commit()
            logger.info(f"Expiring licenses check completed: {len(expiring)} found")
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


async def stop_scheduler() -> None:
    """Stop the background task scheduler."""
    global _scheduler

    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Background scheduler stopped")
