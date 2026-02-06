"""Centralized dependency injection factories for FastAPI.

This module provides reusable service factory functions for dependency injection,
eliminating duplicate definitions across routers.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.database import get_db
from licence_api.services.admin_account_service import AdminAccountService
from licence_api.services.audit_service import AuditService
from licence_api.services.auth_service import AuthService
from licence_api.services.backup_service import BackupService
from licence_api.services.cancellation_service import CancellationService
from licence_api.services.email_service import EmailService
from licence_api.services.employee_service import EmployeeService
from licence_api.services.export_service import ExportService
from licence_api.services.external_account_service import ExternalAccountService
from licence_api.services.import_service import ImportService
from licence_api.services.license_package_service import LicensePackageService
from licence_api.services.license_service import LicenseService
from licence_api.services.manual_employee_service import ManualEmployeeService
from licence_api.services.manual_license_service import ManualLicenseService
from licence_api.services.matching_service import MatchingService
from licence_api.services.notification_service import NotificationService
from licence_api.services.organization_license_service import OrganizationLicenseService
from licence_api.services.payment_method_service import PaymentMethodService
from licence_api.services.pricing_service import PricingService
from licence_api.services.provider_file_service import ProviderFileService
from licence_api.services.provider_service import ProviderService
from licence_api.services.rbac_service import RbacService
from licence_api.services.report_service import ReportService
from licence_api.services.service_account_service import ServiceAccountService
from licence_api.services.settings_service import SettingsService
from licence_api.services.sync_service import SyncService


# =============================================================================
# Core Service Factories
# =============================================================================


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    """Get AuditService instance."""
    return AuditService(db)


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Get AuthService instance."""
    return AuthService(db)


def get_backup_service(db: AsyncSession = Depends(get_db)) -> BackupService:
    """Get BackupService instance."""
    return BackupService(db)


def get_email_service(db: AsyncSession = Depends(get_db)) -> EmailService:
    """Get EmailService instance."""
    return EmailService(db)


def get_settings_service(db: AsyncSession = Depends(get_db)) -> SettingsService:
    """Get SettingsService instance."""
    return SettingsService(db)


def get_notification_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    """Get NotificationService instance."""
    return NotificationService(db)


# =============================================================================
# Provider Service Factories
# =============================================================================


def get_provider_service(db: AsyncSession = Depends(get_db)) -> ProviderService:
    """Get ProviderService instance."""
    return ProviderService(db)


def get_provider_file_service(db: AsyncSession = Depends(get_db)) -> ProviderFileService:
    """Get ProviderFileService instance."""
    return ProviderFileService(db)


def get_sync_service(db: AsyncSession = Depends(get_db)) -> SyncService:
    """Get SyncService instance."""
    return SyncService(db)


def get_pricing_service(db: AsyncSession = Depends(get_db)) -> PricingService:
    """Get PricingService instance."""
    return PricingService(db)


def get_import_service(db: AsyncSession = Depends(get_db)) -> ImportService:
    """Get ImportService instance."""
    return ImportService(db)


# =============================================================================
# License Service Factories
# =============================================================================


def get_license_service(db: AsyncSession = Depends(get_db)) -> LicenseService:
    """Get LicenseService instance."""
    return LicenseService(db)


def get_license_package_service(
    db: AsyncSession = Depends(get_db),
) -> LicensePackageService:
    """Get LicensePackageService instance."""
    return LicensePackageService(db)


def get_organization_license_service(
    db: AsyncSession = Depends(get_db),
) -> OrganizationLicenseService:
    """Get OrganizationLicenseService instance."""
    return OrganizationLicenseService(db)


def get_manual_license_service(
    db: AsyncSession = Depends(get_db),
) -> ManualLicenseService:
    """Get ManualLicenseService instance."""
    return ManualLicenseService(db)


def get_matching_service(db: AsyncSession = Depends(get_db)) -> MatchingService:
    """Get MatchingService instance."""
    return MatchingService(db)


def get_cancellation_service(
    db: AsyncSession = Depends(get_db),
) -> CancellationService:
    """Get CancellationService instance."""
    return CancellationService(db)


# =============================================================================
# Account Service Factories
# =============================================================================


def get_admin_account_service(
    db: AsyncSession = Depends(get_db),
) -> AdminAccountService:
    """Get AdminAccountService instance."""
    return AdminAccountService(db)


def get_service_account_service(
    db: AsyncSession = Depends(get_db),
) -> ServiceAccountService:
    """Get ServiceAccountService instance."""
    return ServiceAccountService(db)


def get_external_account_service(
    db: AsyncSession = Depends(get_db),
) -> ExternalAccountService:
    """Get ExternalAccountService instance."""
    return ExternalAccountService(db)


# =============================================================================
# Employee Service Factories
# =============================================================================


def get_employee_service(db: AsyncSession = Depends(get_db)) -> EmployeeService:
    """Get EmployeeService instance."""
    return EmployeeService(db)


def get_manual_employee_service(
    db: AsyncSession = Depends(get_db),
) -> ManualEmployeeService:
    """Get ManualEmployeeService instance."""
    return ManualEmployeeService(db)


# =============================================================================
# Report & Export Service Factories
# =============================================================================


def get_report_service(db: AsyncSession = Depends(get_db)) -> ReportService:
    """Get ReportService instance."""
    return ReportService(db)


def get_export_service(db: AsyncSession = Depends(get_db)) -> ExportService:
    """Get ExportService instance."""
    return ExportService(db)


# =============================================================================
# Admin Service Factories
# =============================================================================


def get_rbac_service(db: AsyncSession = Depends(get_db)) -> RbacService:
    """Get RbacService instance."""
    return RbacService(db)


def get_payment_method_service(
    db: AsyncSession = Depends(get_db),
) -> PaymentMethodService:
    """Get PaymentMethodService instance."""
    return PaymentMethodService(db)
