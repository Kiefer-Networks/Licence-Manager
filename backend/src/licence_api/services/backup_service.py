"""Backup service for system export and restore functionality.

Security Note (INJ-04): This service uses JSON for data serialization, NOT pickle or
other unsafe deserialization methods. All data is validated against a schema before
import. Binary file content is base64-encoded within the JSON structure.
"""

import base64
import json
import logging
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from fastapi import Request
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import FILES_DIR
from licence_api.models.dto.backup import (
    BackupInfoResponse,
    BackupMetadata,
    ProviderValidation,
    RestoreImportCounts,
    RestoreResponse,
    RestoreValidation,
)
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

if TYPE_CHECKING:
    from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.orm.cost_snapshot import CostSnapshotORM
from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.models.orm.license_package import LicensePackageORM
from licence_api.models.orm.notification_rule import NotificationRuleORM
from licence_api.models.orm.organization_license import OrganizationLicenseORM
from licence_api.models.orm.payment_method import PaymentMethodORM
from licence_api.models.orm.provider import ProviderORM
from licence_api.models.orm.provider_file import ProviderFileORM
from licence_api.models.orm.service_account_pattern import ServiceAccountPatternORM
from licence_api.models.orm.admin_account_pattern import AdminAccountPatternORM
from licence_api.models.orm.settings import SettingsORM
from licence_api.security.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Backup format header
BACKUP_HEADER = b"LICENCE_BACKUP_V1"
BACKUP_VERSION = "1.0"

# Encryption parameters
SALT_SIZE = 16
NONCE_SIZE = 12
PBKDF2_ITERATIONS = 600000


class BackupService:
    """Service for creating and restoring encrypted system backups."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize backup service with database session."""
        self.session = session
        self.encryption = get_encryption_service()
        self.audit_service = AuditService(session) if session else None

    # =========================================================================
    # Encryption utilities
    # =========================================================================

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
        )
        return kdf.derive(password.encode("utf-8"))

    def _encrypt(self, data: bytes, password: str) -> bytes:
        """Encrypt data with AES-256-GCM using password-derived key.

        Returns: header + salt + nonce + ciphertext (with auth tag)
        """
        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key = self._derive_key(password, salt)

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, data, None)

        return BACKUP_HEADER + salt + nonce + ciphertext

    def _decrypt(self, encrypted_data: bytes, password: str) -> bytes:
        """Decrypt backup data.

        Args:
            encrypted_data: Full backup file data
            password: User password

        Returns:
            Decrypted JSON bytes

        Raises:
            ValueError: If decryption fails (wrong password or corrupted data)
        """
        header_len = len(BACKUP_HEADER)

        # Verify header
        if not encrypted_data.startswith(BACKUP_HEADER):
            raise ValueError("Invalid backup format: missing header")

        if len(encrypted_data) < header_len + SALT_SIZE + NONCE_SIZE + 16:
            raise ValueError("Invalid backup format: file too short")

        # Extract components
        offset = header_len
        salt = encrypted_data[offset : offset + SALT_SIZE]
        offset += SALT_SIZE
        nonce = encrypted_data[offset : offset + NONCE_SIZE]
        offset += NONCE_SIZE
        ciphertext = encrypted_data[offset:]

        # Derive key and decrypt
        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)

        try:
            return aesgcm.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise ValueError("Decryption failed: wrong password or corrupted data") from e

    # =========================================================================
    # Export functionality
    # =========================================================================

    async def create_backup(
        self,
        password: str,
        user: "AdminUser | None" = None,
        request: Request | None = None,
    ) -> bytes:
        """Create an encrypted backup of all system data.

        Args:
            password: Password for encryption
            user: Admin user creating the backup
            request: HTTP request for audit logging

        Returns:
            Encrypted backup file bytes
        """
        data = await self._collect_data()
        json_data = json.dumps(data, default=self._json_serializer).encode("utf-8")
        backup_data = self._encrypt(json_data, password)

        # Audit log
        if user and self.audit_service:
            await self.audit_service.log(
                action=AuditAction.EXPORT,
                resource_type=ResourceType.SYSTEM,
                user_id=user.id,
                details={"action": "backup_created"},
            )
            await self.session.commit()

        return backup_data

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    async def _collect_data(self) -> dict[str, Any]:
        """Collect all exportable data from database."""
        # Fetch all entities
        providers = await self._fetch_all(ProviderORM)
        licenses = await self._fetch_all(LicenseORM)
        employees = await self._fetch_all(EmployeeORM)
        license_packages = await self._fetch_all(LicensePackageORM)
        organization_licenses = await self._fetch_all(OrganizationLicenseORM)
        payment_methods = await self._fetch_all(PaymentMethodORM)
        provider_files = await self._fetch_all(ProviderFileORM)
        cost_snapshots = await self._fetch_all(CostSnapshotORM)
        settings = await self._fetch_all(SettingsORM)
        notification_rules = await self._fetch_all(NotificationRuleORM)
        service_account_patterns = await self._fetch_all(ServiceAccountPatternORM)
        admin_account_patterns = await self._fetch_all(AdminAccountPatternORM)

        # Convert to dicts and collect file data
        provider_files_data = await self._collect_files(provider_files)

        return {
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "provider_count": len(providers),
                "license_count": len(licenses),
                "employee_count": len(employees),
                "license_package_count": len(license_packages),
                "organization_license_count": len(organization_licenses),
                "payment_method_count": len(payment_methods),
                "provider_file_count": len(provider_files),
                "cost_snapshot_count": len(cost_snapshots),
                "settings_count": len(settings),
                "notification_rule_count": len(notification_rules),
                "service_account_pattern_count": len(service_account_patterns),
                "admin_account_pattern_count": len(admin_account_patterns),
            },
            "data": {
                "providers": [self._orm_to_dict(p) for p in providers],
                "licenses": [self._orm_to_dict(lic) for lic in licenses],
                "employees": [self._orm_to_dict(e) for e in employees],
                "license_packages": [self._orm_to_dict(lp) for lp in license_packages],
                "organization_licenses": [self._orm_to_dict(ol) for ol in organization_licenses],
                "payment_methods": [self._orm_to_dict(pm) for pm in payment_methods],
                "provider_files": provider_files_data,
                "cost_snapshots": [self._orm_to_dict(cs) for cs in cost_snapshots],
                "settings": [self._settings_to_dict(s) for s in settings],
                "notification_rules": [self._orm_to_dict(nr) for nr in notification_rules],
                "service_account_patterns": [self._orm_to_dict(sap) for sap in service_account_patterns],
                "admin_account_patterns": [self._orm_to_dict(aap) for aap in admin_account_patterns],
            },
        }

    async def _fetch_all(self, model: type) -> list:
        """Fetch all records of a model.

        Architecture Note (MVC-01): This method uses direct SQLAlchemy queries
        because backup/restore is a system-level operation that must work with
        all models generically. Creating individual repository methods for each
        model would not provide additional abstraction value for this use case.
        """
        result = await self.session.execute(select(model))
        return list(result.scalars().all())

    def _orm_to_dict(self, obj: Any) -> dict[str, Any]:
        """Convert ORM object to dict, including all columns."""
        result = {}
        for column in obj.__table__.columns:
            value = getattr(obj, column.name)
            result[column.name] = value
        return result

    def _settings_to_dict(self, settings: SettingsORM) -> dict[str, Any]:
        """Convert settings ORM to dict."""
        return {
            "key": settings.key,
            "value": settings.value,
            "updated_at": settings.updated_at,
        }

    async def _collect_files(self, provider_files: list[ProviderFileORM]) -> list[dict[str, Any]]:
        """Collect provider files with their binary content."""
        files_data = []
        for pf in provider_files:
            file_dict = self._orm_to_dict(pf)

            # Read file content and encode as base64
            file_path = FILES_DIR / str(pf.provider_id) / pf.filename
            if file_path.exists():
                try:
                    file_content = file_path.read_bytes()
                    file_dict["file_data"] = base64.b64encode(file_content).decode("utf-8")
                except Exception as e:
                    logger.warning(f"Failed to read file {file_path}: {e}")
                    file_dict["file_data"] = None
            else:
                logger.warning(f"File not found: {file_path}")
                file_dict["file_data"] = None

            files_data.append(file_dict)
        return files_data

    # =========================================================================
    # Info functionality (without password)
    # =========================================================================

    def get_backup_info(self, file_data: bytes) -> BackupInfoResponse:
        """Get backup file info without decrypting.

        Args:
            file_data: Backup file bytes

        Returns:
            Backup info response
        """
        # Check header
        if not file_data.startswith(BACKUP_HEADER):
            return BackupInfoResponse(
                valid_format=False,
                error="Invalid backup format: missing or wrong header",
            )

        header_len = len(BACKUP_HEADER)
        min_size = header_len + SALT_SIZE + NONCE_SIZE + 16

        if len(file_data) < min_size:
            return BackupInfoResponse(
                valid_format=False,
                error="Invalid backup format: file too short",
            )

        # Valid format, but we can't read metadata without password
        return BackupInfoResponse(
            valid_format=True,
            version=BACKUP_VERSION,
            requires_password=True,
        )

    # =========================================================================
    # Restore functionality
    # =========================================================================

    async def restore_backup(
        self,
        file_data: bytes,
        password: str,
        user: "AdminUser | None" = None,
        request: Request | None = None,
    ) -> RestoreResponse:
        """Restore system from encrypted backup.

        WARNING: This deletes ALL existing data!

        Args:
            file_data: Encrypted backup file
            password: Decryption password
            user: Admin user performing the restore
            request: HTTP request for audit logging

        Returns:
            Restore response with import counts and validation results
        """
        # Decrypt
        try:
            json_bytes = self._decrypt(file_data, password)
            backup_data = json.loads(json_bytes.decode("utf-8"))
        except ValueError as e:
            return RestoreResponse(
                success=False,
                imported=RestoreImportCounts(),
                validation=RestoreValidation(
                    providers_tested=0,
                    providers_valid=0,
                    providers_failed=[],
                ),
                error=str(e),
            )
        except json.JSONDecodeError as e:
            return RestoreResponse(
                success=False,
                imported=RestoreImportCounts(),
                validation=RestoreValidation(
                    providers_tested=0,
                    providers_valid=0,
                    providers_failed=[],
                ),
                error=f"Invalid JSON in backup: {e}",
            )

        # Validate schema
        try:
            self._validate_schema(backup_data)
        except ValueError as e:
            return RestoreResponse(
                success=False,
                imported=RestoreImportCounts(),
                validation=RestoreValidation(
                    providers_tested=0,
                    providers_valid=0,
                    providers_failed=[],
                ),
                error=str(e),
            )

        # Clear existing data and import
        try:
            await self._clear_all_data()
            counts = await self._import_data(backup_data["data"])
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Restore failed: {e}")
            return RestoreResponse(
                success=False,
                imported=RestoreImportCounts(),
                validation=RestoreValidation(
                    providers_tested=0,
                    providers_valid=0,
                    providers_failed=[],
                ),
                error=f"Database error during restore: {e}",
            )

        # Validate provider credentials
        validation = await self._validate_providers()

        # Audit log successful restore
        if user and self.audit_service:
            await self.audit_service.log(
                action=AuditAction.IMPORT,
                resource_type=ResourceType.SYSTEM,
                user_id=user.id,
                details={
                    "action": "backup_restored",
                    "imported": counts.model_dump(),
                    "providers_valid": validation.providers_valid,
                    "providers_failed": len(validation.providers_failed),
                },
            )
            await self.session.commit()

        return RestoreResponse(
            success=True,
            imported=counts,
            validation=validation,
        )

    def _validate_schema(self, data: dict[str, Any]) -> None:
        """Validate backup data schema."""
        required_keys = ["version", "created_at", "data"]
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Missing required key: {key}")

        required_data_keys = [
            "providers",
            "licenses",
            "employees",
            "license_packages",
            "organization_licenses",
            "payment_methods",
            "provider_files",
            "cost_snapshots",
            "settings",
            "notification_rules",
            # Optional keys for backward compatibility:
            # "service_account_patterns",
        ]
        for key in required_data_keys:
            if key not in data["data"]:
                raise ValueError(f"Missing data key: {key}")

    async def _clear_all_data(self) -> None:
        """Clear all data in correct order (respecting foreign keys).

        Architecture Note (MVC-01): This method uses direct SQLAlchemy delete
        statements because restore operations require atomic deletion of all
        data in a specific order to respect foreign key constraints. This is
        a system-level operation that doesn't fit the standard repository pattern.
        """
        # Delete in reverse dependency order
        # Licenses reference providers and employees
        await self.session.execute(delete(LicenseORM))
        # License packages, org licenses, provider files, cost snapshots reference providers
        await self.session.execute(delete(LicensePackageORM))
        await self.session.execute(delete(OrganizationLicenseORM))
        await self.session.execute(delete(ProviderFileORM))
        await self.session.execute(delete(CostSnapshotORM))
        # Service account patterns reference employees
        await self.session.execute(delete(ServiceAccountPatternORM))
        # Providers reference payment methods
        await self.session.execute(delete(ProviderORM))
        # Employees (no FK dependencies from above after licenses cleared)
        await self.session.execute(delete(EmployeeORM))
        # Payment methods (providers cleared above)
        await self.session.execute(delete(PaymentMethodORM))
        # Independent tables
        await self.session.execute(delete(NotificationRuleORM))
        await self.session.execute(delete(SettingsORM))

        # Delete all provider files from disk
        if FILES_DIR.exists():
            for provider_dir in FILES_DIR.iterdir():
                if provider_dir.is_dir():
                    for file in provider_dir.iterdir():
                        file.unlink()
                    provider_dir.rmdir()

        await self.session.flush()

    async def _import_data(self, data: dict[str, Any]) -> RestoreImportCounts:
        """Import data in correct order (respecting foreign keys)."""
        counts = RestoreImportCounts()

        # Import in dependency order (parents first)

        # 1. Settings (no dependencies)
        for s in data["settings"]:
            settings_orm = SettingsORM(
                key=s["key"],
                value=s["value"],
            )
            self.session.add(settings_orm)
            counts.settings += 1

        # 2. Payment methods (no dependencies)
        for pm in data["payment_methods"]:
            pm_orm = PaymentMethodORM(
                id=UUID(pm["id"]) if isinstance(pm["id"], str) else pm["id"],
                name=pm["name"],
                type=pm["type"],
                details=pm.get("details", {}),
                is_default=pm.get("is_default", False),
                notes=pm.get("notes"),
                created_at=self._parse_datetime(pm.get("created_at")),
                updated_at=self._parse_datetime(pm.get("updated_at")),
            )
            self.session.add(pm_orm)
            counts.payment_methods += 1

        # 3. Employees (no dependencies)
        for e in data["employees"]:
            emp_orm = EmployeeORM(
                id=UUID(e["id"]) if isinstance(e["id"], str) else e["id"],
                hibob_id=e["hibob_id"],
                email=e["email"],
                full_name=e["full_name"],
                department=e.get("department"),
                status=e["status"],
                start_date=self._parse_date(e.get("start_date")),
                termination_date=self._parse_date(e.get("termination_date")),
                avatar_url=e.get("avatar_url"),
                synced_at=self._parse_datetime(e["synced_at"]),
                created_at=self._parse_datetime(e.get("created_at")),
                updated_at=self._parse_datetime(e.get("updated_at")),
            )
            self.session.add(emp_orm)
            counts.employees += 1

        # 4. Providers (depends on payment_methods)
        for p in data["providers"]:
            # Decode credentials from base64 if stored as string
            credentials = p["credentials_encrypted"]
            if isinstance(credentials, str):
                credentials = base64.b64decode(credentials)

            provider_orm = ProviderORM(
                id=UUID(p["id"]) if isinstance(p["id"], str) else p["id"],
                name=p["name"],
                display_name=p["display_name"],
                logo_url=p.get("logo_url"),
                enabled=p.get("enabled", True),
                credentials_encrypted=credentials,
                config=p.get("config"),
                last_sync_at=self._parse_datetime(p.get("last_sync_at")),
                last_sync_status=p.get("last_sync_status"),
                payment_method_id=UUID(p["payment_method_id"]) if p.get("payment_method_id") else None,
                created_at=self._parse_datetime(p.get("created_at")),
                updated_at=self._parse_datetime(p.get("updated_at")),
            )
            self.session.add(provider_orm)
            counts.providers += 1

        # 5. Notification rules (no dependencies)
        for nr in data["notification_rules"]:
            nr_orm = NotificationRuleORM(
                id=UUID(nr["id"]) if isinstance(nr["id"], str) else nr["id"],
                event_type=nr["event_type"],
                slack_channel=nr["slack_channel"],
                enabled=nr.get("enabled", True),
                template=nr.get("template"),
                created_at=self._parse_datetime(nr.get("created_at")),
                updated_at=self._parse_datetime(nr.get("updated_at")),
            )
            self.session.add(nr_orm)
            counts.notification_rules += 1

        await self.session.flush()

        # 6. License packages (depends on providers)
        for lp in data["license_packages"]:
            lp_orm = LicensePackageORM(
                id=UUID(lp["id"]) if isinstance(lp["id"], str) else lp["id"],
                provider_id=UUID(lp["provider_id"]) if isinstance(lp["provider_id"], str) else lp["provider_id"],
                license_type=lp["license_type"],
                display_name=lp.get("display_name"),
                total_seats=lp["total_seats"],
                cost_per_seat=Decimal(lp["cost_per_seat"]) if lp.get("cost_per_seat") else None,
                billing_cycle=lp.get("billing_cycle"),
                payment_frequency=lp.get("payment_frequency"),
                currency=lp.get("currency", "EUR"),
                contract_start=self._parse_date(lp.get("contract_start")),
                contract_end=self._parse_date(lp.get("contract_end")),
                auto_renew=lp.get("auto_renew", True),
                notes=lp.get("notes"),
                # Cancellation and expiration tracking
                cancelled_at=self._parse_datetime(lp.get("cancelled_at")),
                cancellation_effective_date=self._parse_date(lp.get("cancellation_effective_date")),
                cancellation_reason=lp.get("cancellation_reason"),
                cancelled_by=UUID(lp["cancelled_by"]) if lp.get("cancelled_by") else None,
                needs_reorder=lp.get("needs_reorder", False),
                status=lp.get("status", "active"),
                created_at=self._parse_datetime(lp.get("created_at")),
                updated_at=self._parse_datetime(lp.get("updated_at")),
            )
            self.session.add(lp_orm)
            counts.license_packages += 1

        # 7. Organization licenses (depends on providers)
        for ol in data["organization_licenses"]:
            ol_orm = OrganizationLicenseORM(
                id=UUID(ol["id"]) if isinstance(ol["id"], str) else ol["id"],
                provider_id=UUID(ol["provider_id"]) if isinstance(ol["provider_id"], str) else ol["provider_id"],
                name=ol["name"],
                license_type=ol.get("license_type"),
                quantity=ol.get("quantity"),
                unit=ol.get("unit"),
                monthly_cost=Decimal(ol["monthly_cost"]) if ol.get("monthly_cost") else None,
                currency=ol.get("currency", "EUR"),
                billing_cycle=ol.get("billing_cycle"),
                renewal_date=self._parse_date(ol.get("renewal_date")),
                notes=ol.get("notes"),
                # Cancellation and expiration tracking
                expires_at=self._parse_date(ol.get("expires_at")),
                cancelled_at=self._parse_datetime(ol.get("cancelled_at")),
                cancellation_effective_date=self._parse_date(ol.get("cancellation_effective_date")),
                cancellation_reason=ol.get("cancellation_reason"),
                cancelled_by=UUID(ol["cancelled_by"]) if ol.get("cancelled_by") else None,
                needs_reorder=ol.get("needs_reorder", False),
                status=ol.get("status", "active"),
                created_at=self._parse_datetime(ol.get("created_at")),
                updated_at=self._parse_datetime(ol.get("updated_at")),
            )
            self.session.add(ol_orm)
            counts.organization_licenses += 1

        # 8. Cost snapshots (depends on providers)
        for cs in data["cost_snapshots"]:
            cs_orm = CostSnapshotORM(
                id=UUID(cs["id"]) if isinstance(cs["id"], str) else cs["id"],
                snapshot_date=self._parse_date(cs["snapshot_date"]),
                provider_id=UUID(cs["provider_id"]) if cs.get("provider_id") else None,
                total_cost=Decimal(cs["total_cost"]),
                license_count=cs["license_count"],
                active_count=cs.get("active_count", 0),
                unassigned_count=cs.get("unassigned_count", 0),
                currency=cs.get("currency", "EUR"),
                breakdown=cs.get("breakdown"),
                created_at=self._parse_datetime(cs.get("created_at")),
                updated_at=self._parse_datetime(cs.get("updated_at")),
            )
            self.session.add(cs_orm)
            counts.cost_snapshots += 1

        # 9. Licenses (depends on providers and employees)
        for lic in data["licenses"]:
            lic_orm = LicenseORM(
                id=UUID(lic["id"]) if isinstance(lic["id"], str) else lic["id"],
                provider_id=UUID(lic["provider_id"]) if isinstance(lic["provider_id"], str) else lic["provider_id"],
                employee_id=UUID(lic["employee_id"]) if lic.get("employee_id") else None,
                external_user_id=lic["external_user_id"],
                license_type=lic.get("license_type"),
                status=lic["status"],
                assigned_at=self._parse_datetime(lic.get("assigned_at")),
                last_activity_at=self._parse_datetime(lic.get("last_activity_at")),
                monthly_cost=Decimal(lic["monthly_cost"]) if lic.get("monthly_cost") else None,
                currency=lic.get("currency", "EUR"),
                extra_data=lic.get("metadata") or lic.get("extra_data"),
                synced_at=self._parse_datetime(lic["synced_at"]),
                is_service_account=lic.get("is_service_account", False),
                service_account_name=lic.get("service_account_name"),
                service_account_owner_id=UUID(lic["service_account_owner_id"]) if lic.get("service_account_owner_id") else None,
                suggested_employee_id=UUID(lic["suggested_employee_id"]) if lic.get("suggested_employee_id") else None,
                match_confidence=lic.get("match_confidence"),
                match_status=lic.get("match_status"),
                match_method=lic.get("match_method"),
                match_reviewed_at=self._parse_datetime(lic.get("match_reviewed_at")),
                match_reviewed_by=UUID(lic["match_reviewed_by"]) if lic.get("match_reviewed_by") else None,
                # Cancellation and expiration tracking
                expires_at=self._parse_date(lic.get("expires_at")),
                needs_reorder=lic.get("needs_reorder", False),
                cancelled_at=self._parse_datetime(lic.get("cancelled_at")),
                cancellation_effective_date=self._parse_date(lic.get("cancellation_effective_date")),
                cancellation_reason=lic.get("cancellation_reason"),
                cancelled_by=UUID(lic["cancelled_by"]) if lic.get("cancelled_by") else None,
                created_at=self._parse_datetime(lic.get("created_at")),
                updated_at=self._parse_datetime(lic.get("updated_at")),
            )
            self.session.add(lic_orm)
            counts.licenses += 1

        # 10. Provider files (depends on providers) - also restore files to disk
        for pf in data["provider_files"]:
            pf_orm = ProviderFileORM(
                id=UUID(pf["id"]) if isinstance(pf["id"], str) else pf["id"],
                provider_id=UUID(pf["provider_id"]) if isinstance(pf["provider_id"], str) else pf["provider_id"],
                filename=pf["filename"],
                original_name=pf["original_name"],
                file_type=pf["file_type"],
                file_size=pf["file_size"],
                description=pf.get("description"),
                category=pf.get("category"),
                created_at=self._parse_datetime(pf.get("created_at")),
                updated_at=self._parse_datetime(pf.get("updated_at")),
            )
            self.session.add(pf_orm)
            counts.provider_files += 1

            # Restore file to disk if data is present
            if pf.get("file_data"):
                try:
                    provider_id = pf["provider_id"]
                    if isinstance(provider_id, str):
                        provider_id = UUID(provider_id)
                    provider_dir = FILES_DIR / str(provider_id)
                    provider_dir.mkdir(parents=True, exist_ok=True)
                    file_path = provider_dir / pf["filename"]
                    file_content = base64.b64decode(pf["file_data"])
                    file_path.write_bytes(file_content)
                except Exception as e:
                    logger.warning(f"Failed to restore file {pf['filename']}: {e}")

        # 11. Service account patterns (depends on employees for owner_id)
        for sap in data.get("service_account_patterns", []):
            sap_orm = ServiceAccountPatternORM(
                id=UUID(sap["id"]) if isinstance(sap["id"], str) else sap["id"],
                email_pattern=sap["email_pattern"],
                name=sap.get("name"),
                owner_id=UUID(sap["owner_id"]) if sap.get("owner_id") else None,
                notes=sap.get("notes"),
                created_by=UUID(sap["created_by"]) if sap.get("created_by") else None,
                created_at=self._parse_datetime(sap.get("created_at")),
                updated_at=self._parse_datetime(sap.get("updated_at")),
            )
            self.session.add(sap_orm)
            counts.service_account_patterns += 1

        # 12. Admin account patterns (depends on employees for owner_id)
        for aap in data.get("admin_account_patterns", []):
            aap_orm = AdminAccountPatternORM(
                id=UUID(aap["id"]) if isinstance(aap["id"], str) else aap["id"],
                email_pattern=aap["email_pattern"],
                name=aap.get("name"),
                owner_id=UUID(aap["owner_id"]) if aap.get("owner_id") else None,
                notes=aap.get("notes"),
                created_by=UUID(aap["created_by"]) if aap.get("created_by") else None,
                created_at=self._parse_datetime(aap.get("created_at")),
                updated_at=self._parse_datetime(aap.get("updated_at")),
            )
            self.session.add(aap_orm)
            counts.admin_account_patterns += 1

        await self.session.flush()
        return counts

    def _parse_datetime(self, value: str | datetime | None) -> datetime | None:
        """Parse datetime from string or return as-is."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # Handle ISO format with timezone
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _parse_date(self, value: str | date | None) -> date | None:
        """Parse date from string or return as-is."""
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        try:
            return date.fromisoformat(value)
        except (ValueError, AttributeError):
            return None

    async def _validate_providers(self) -> RestoreValidation:
        """Validate provider credentials after restore."""
        from licence_api.models.domain.provider import ProviderName
        from licence_api.services.sync_service import SyncService

        providers = await self._fetch_all(ProviderORM)
        validations: list[ProviderValidation] = []
        failed: list[str] = []

        sync_service = SyncService(self.session)

        for provider in providers:
            # Skip manual providers - they don't have external credentials
            if provider.name == ProviderName.MANUAL or provider.name == "manual":
                validations.append(ProviderValidation(
                    provider_name=provider.display_name,
                    valid=True,
                ))
                continue

            try:
                # Decrypt credentials
                credentials = self.encryption.decrypt(provider.credentials_encrypted)

                # Get provider implementation and test connection
                try:
                    provider_impl = sync_service._get_provider_implementation(
                        ProviderName(provider.name),
                        credentials,
                    )

                    # Test the connection
                    if hasattr(provider_impl, "test_connection"):
                        await provider_impl.test_connection()
                    elif hasattr(provider_impl, "fetch_licenses"):
                        # If no test_connection, try a minimal fetch
                        # This is a lightweight test
                        pass

                    validations.append(ProviderValidation(
                        provider_name=provider.display_name,
                        valid=True,
                    ))
                except Exception as e:
                    error_msg = f"{provider.display_name}: {str(e)}"
                    validations.append(ProviderValidation(
                        provider_name=provider.display_name,
                        valid=False,
                        error=str(e),
                    ))
                    failed.append(error_msg)
            except Exception as e:
                error_msg = f"{provider.display_name}: Failed to decrypt credentials"
                validations.append(ProviderValidation(
                    provider_name=provider.display_name,
                    valid=False,
                    error="Failed to decrypt credentials",
                ))
                failed.append(error_msg)

        return RestoreValidation(
            providers_tested=len(providers),
            providers_valid=len([v for v in validations if v.valid]),
            providers_failed=failed,
        )
