"""Backup DTOs for export/import functionality."""

from datetime import datetime
from pydantic import BaseModel, Field


class BackupExportRequest(BaseModel):
    """Request to create an encrypted backup."""

    password: str = Field(min_length=8, max_length=256, description="Password for encryption (8-256 chars)")


class BackupMetadata(BaseModel):
    """Metadata about a backup file."""

    # User and access control
    admin_user_count: int = 0
    role_count: int = 0
    permission_count: int = 0
    user_role_count: int = 0
    role_permission_count: int = 0
    user_notification_preference_count: int = 0

    # Core business data
    provider_count: int = 0
    license_count: int = 0
    employee_count: int = 0
    employee_external_account_count: int = 0
    license_package_count: int = 0
    organization_license_count: int = 0
    payment_method_count: int = 0
    provider_file_count: int = 0
    cost_snapshot_count: int = 0

    # Configuration
    settings_count: int = 0
    notification_rule_count: int = 0
    service_account_pattern_count: int = 0
    admin_account_pattern_count: int = 0
    service_account_license_type_count: int = 0


class BackupInfoResponse(BaseModel):
    """Response with backup file information (before decryption)."""

    valid_format: bool
    version: str | None = None
    created_at: datetime | None = None
    requires_password: bool = True
    compressed: bool = False
    integrity_hash: str | None = None
    error: str | None = None


class ProviderValidation(BaseModel):
    """Validation result for a single provider after restore."""

    provider_name: str
    valid: bool
    error: str | None = None


class RestoreImportCounts(BaseModel):
    """Counts of imported entities during restore."""

    # User and access control
    admin_users: int = 0
    roles: int = 0
    permissions: int = 0
    user_roles: int = 0
    role_permissions: int = 0
    user_notification_preferences: int = 0

    # Core business data
    providers: int = 0
    licenses: int = 0
    employees: int = 0
    employee_external_accounts: int = 0
    license_packages: int = 0
    organization_licenses: int = 0
    payment_methods: int = 0
    provider_files: int = 0
    cost_snapshots: int = 0

    # Configuration
    settings: int = 0
    notification_rules: int = 0
    service_account_patterns: int = 0
    admin_account_patterns: int = 0
    service_account_license_types: int = 0

    # Audit
    audit_logs: int = 0


class RestoreValidation(BaseModel):
    """Validation results for providers after restore."""

    providers_tested: int
    providers_valid: int
    providers_failed: list[str] = Field(max_length=100)  # List of "ProviderName: Error message"


class RestoreResponse(BaseModel):
    """Response after restoring a backup."""

    success: bool
    imported: RestoreImportCounts
    validation: RestoreValidation
    error: str | None = None
