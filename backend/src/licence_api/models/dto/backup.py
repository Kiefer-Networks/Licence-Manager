"""Backup DTOs for export/import functionality."""

from datetime import datetime
from pydantic import BaseModel, Field


class BackupExportRequest(BaseModel):
    """Request to create an encrypted backup."""

    password: str = Field(min_length=8, description="Password for encryption (min 8 chars)")


class BackupMetadata(BaseModel):
    """Metadata about a backup file."""

    provider_count: int
    license_count: int
    employee_count: int
    license_package_count: int
    organization_license_count: int
    payment_method_count: int
    provider_file_count: int
    cost_snapshot_count: int
    settings_count: int
    notification_rule_count: int


class BackupInfoResponse(BaseModel):
    """Response with backup file information (before decryption)."""

    valid_format: bool
    version: str | None = None
    created_at: datetime | None = None
    requires_password: bool = True
    error: str | None = None


class ProviderValidation(BaseModel):
    """Validation result for a single provider after restore."""

    provider_name: str
    valid: bool
    error: str | None = None


class RestoreImportCounts(BaseModel):
    """Counts of imported entities during restore."""

    providers: int = 0
    licenses: int = 0
    employees: int = 0
    license_packages: int = 0
    organization_licenses: int = 0
    payment_methods: int = 0
    provider_files: int = 0
    cost_snapshots: int = 0
    settings: int = 0
    notification_rules: int = 0
    service_account_patterns: int = 0
    admin_account_patterns: int = 0


class RestoreValidation(BaseModel):
    """Validation results for providers after restore."""

    providers_tested: int
    providers_valid: int
    providers_failed: list[str]  # List of "ProviderName: Error message"


class RestoreResponse(BaseModel):
    """Response after restoring a backup."""

    success: bool
    imported: RestoreImportCounts
    validation: RestoreValidation
    error: str | None = None
