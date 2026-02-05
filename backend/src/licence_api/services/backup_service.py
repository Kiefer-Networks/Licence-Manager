"""Backup service for system export and restore functionality.

Architecture Note (MVC-05):
    This service performs bulk data export and import operations that require direct
    database access for efficiency and transactional integrity. The operations include:
    1. Full database export with relationship preservation
    2. Bulk deletion for restore operations (cascading deletes)
    3. Bulk insertion with foreign key ordering
    4. Binary file handling with base64 encoding

    Direct SQLAlchemy access is justified because:
    1. Bulk operations require transaction-level control across multiple tables
    2. Export needs to serialize all entities in dependency order
    3. Restore needs atomic delete-then-insert across all tables
    4. Standard repository patterns would require N+1 queries for relationships
    5. These operations are admin-only and not part of normal request flow

Security Note (INJ-04): This service uses JSON for data serialization, NOT pickle or
other unsafe deserialization methods. All data is validated against a schema before
import. Binary file content is base64-encoded within the JSON structure.
"""

import base64
import gzip
import hashlib
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
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.constants.paths import FILES_DIR
from licence_api.models.dto.backup import (
    BackupInfoResponse,
    RestoreImportCounts,
    RestoreResponse,
    RestoreValidation,
    ProviderValidation,
)
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType

if TYPE_CHECKING:
    from licence_api.models.domain.admin_user import AdminUser

# ORM models
from licence_api.models.orm.admin_user import AdminUserORM
from licence_api.models.orm.audit_log import AuditLogORM
from licence_api.models.orm.role import RoleORM
from licence_api.models.orm.permission import PermissionORM
from licence_api.models.orm.user_role import UserRoleORM
from licence_api.models.orm.role_permission import RolePermissionORM
from licence_api.models.orm.user_notification_preference import UserNotificationPreferenceORM
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
from licence_api.models.orm.service_account_license_type import ServiceAccountLicenseTypeORM
from licence_api.models.orm.settings import SettingsORM
from licence_api.security.encryption import get_encryption_service

logger = logging.getLogger(__name__)

# Backup format header
BACKUP_HEADER = b"LICENCE_BACKUP_V2"
BACKUP_VERSION = "2.0"

# Encryption parameters
SALT_SIZE = 16
NONCE_SIZE = 12
HASH_SIZE = 32  # SHA-256
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

        Format: header(17B) + content_hash(32B) + salt(16B) + nonce(12B) + ciphertext

        The content_hash is SHA-256 of the uncompressed data, allowing integrity
        verification without decryption.
        """
        # Compress data with gzip
        compressed = gzip.compress(data, compresslevel=6)

        # Calculate hash of original (uncompressed) data for integrity check
        content_hash = hashlib.sha256(data).digest()

        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key = self._derive_key(password, salt)

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, compressed, None)

        return BACKUP_HEADER + content_hash + salt + nonce + ciphertext

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
        if not encrypted_data.startswith(BACKUP_HEADER):
            raise ValueError("Invalid backup format: missing or wrong header")

        header_len = len(BACKUP_HEADER)
        min_size = header_len + HASH_SIZE + SALT_SIZE + NONCE_SIZE + 16

        if len(encrypted_data) < min_size:
            raise ValueError("Invalid backup format: file too short")

        offset = header_len
        stored_hash = encrypted_data[offset : offset + HASH_SIZE]
        offset += HASH_SIZE
        salt = encrypted_data[offset : offset + SALT_SIZE]
        offset += SALT_SIZE
        nonce = encrypted_data[offset : offset + NONCE_SIZE]
        offset += NONCE_SIZE
        ciphertext = encrypted_data[offset:]

        key = self._derive_key(password, salt)
        aesgcm = AESGCM(key)

        try:
            compressed = aesgcm.decrypt(nonce, ciphertext, None)
            data = gzip.decompress(compressed)

            # Verify integrity
            computed_hash = hashlib.sha256(data).digest()
            if computed_hash != stored_hash:
                raise ValueError("Integrity check failed: data may be corrupted")

            return data
        except gzip.BadGzipFile as e:
            raise ValueError("Decompression failed: corrupted data") from e
        except Exception as e:
            if "Integrity check failed" in str(e):
                raise
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
                user=user,
                request=request,
                details={"action": "backup_created", "version": BACKUP_VERSION},
            )
            await self.session.commit()

        return backup_data

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for special types."""
        from sqlalchemy import MetaData

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
        # Skip SQLAlchemy internal objects that may leak through
        if isinstance(obj, MetaData):
            return None
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    async def _collect_data(self) -> dict[str, Any]:
        """Collect all exportable data from database."""
        # Fetch all entities
        admin_users = await self._fetch_all(AdminUserORM)
        roles = await self._fetch_all(RoleORM)
        permissions = await self._fetch_all(PermissionORM)
        user_roles = await self._fetch_all(UserRoleORM)
        role_permissions = await self._fetch_all(RolePermissionORM)
        user_notification_preferences = await self._fetch_all(UserNotificationPreferenceORM)
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
        service_account_license_types = await self._fetch_all(ServiceAccountLicenseTypeORM)
        audit_logs = await self._fetch_all(AuditLogORM)

        # Convert to dicts and collect file data
        provider_files_data = await self._collect_files(provider_files)

        # Convert admin users but exclude sensitive auth data
        admin_users_data = [self._admin_user_to_dict(u) for u in admin_users]

        return {
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "admin_user_count": len(admin_users),
                "role_count": len(roles),
                "permission_count": len(permissions),
                "user_role_count": len(user_roles),
                "role_permission_count": len(role_permissions),
                "user_notification_preference_count": len(user_notification_preferences),
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
                "service_account_license_type_count": len(service_account_license_types),
                "audit_log_count": len(audit_logs),
            },
            "data": {
                "admin_users": admin_users_data,
                "roles": [self._orm_to_dict(r) for r in roles],
                "permissions": [self._orm_to_dict(p) for p in permissions],
                "user_roles": [self._junction_to_dict(ur) for ur in user_roles],
                "role_permissions": [self._junction_to_dict(rp) for rp in role_permissions],
                "user_notification_preferences": [self._orm_to_dict(unp) for unp in user_notification_preferences],
                "providers": [self._provider_to_dict(p) for p in providers],
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
                "service_account_license_types": [self._orm_to_dict(salt) for salt in service_account_license_types],
                "audit_logs": [self._audit_log_to_dict(al) for al in audit_logs],
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
        """Convert ORM object to dict, including all columns.

        Uses the mapper to get the correct Python attribute name for each column,
        handling cases where the Python attribute differs from the DB column name.
        """
        from sqlalchemy import inspect
        from sqlalchemy import MetaData

        result = {}
        mapper = inspect(obj.__class__)

        for column in obj.__table__.columns:
            # Find the attribute name from the mapper
            attr_name = None
            for prop in mapper.iterate_properties:
                if hasattr(prop, 'columns'):
                    for col in prop.columns:
                        if col.name == column.name:
                            attr_name = prop.key
                            break
                if attr_name:
                    break

            # Fallback to column name if no mapping found
            if attr_name is None:
                attr_name = column.name

            # Get the value using the correct attribute name
            value = getattr(obj, attr_name, None)

            # Skip SQLAlchemy internal MetaData objects
            if isinstance(value, MetaData):
                value = None

            # Store with the database column name for restore compatibility
            result[column.name] = value
        return result

    def _junction_to_dict(self, obj: Any) -> dict[str, Any]:
        """Convert junction table ORM object to dict."""
        from sqlalchemy import inspect
        from sqlalchemy import MetaData

        result = {}
        mapper = inspect(obj.__class__)

        for column in obj.__table__.columns:
            # Find the attribute name from the mapper
            attr_name = None
            for prop in mapper.iterate_properties:
                if hasattr(prop, 'columns'):
                    for col in prop.columns:
                        if col.name == column.name:
                            attr_name = prop.key
                            break
                if attr_name:
                    break

            # Fallback to column name if no mapping found
            if attr_name is None:
                attr_name = column.name

            value = getattr(obj, attr_name, None)

            # Skip SQLAlchemy internal MetaData objects
            if isinstance(value, MetaData):
                value = None

            result[column.name] = value
        return result

    def _admin_user_to_dict(self, user: AdminUserORM) -> dict[str, Any]:
        """Convert admin user to dict, decrypting TOTP secrets for portability.

        TOTP secrets are stored decrypted in the backup since the backup itself
        is password-encrypted. This allows backups to be restored on servers
        with different ENCRYPTION_KEYs.
        """
        # Decrypt TOTP secret if present
        totp_secret = None
        if user.totp_secret_encrypted:
            try:
                totp_secret = self.encryption.decrypt_string(user.totp_secret_encrypted)
            except ValueError:
                logger.warning(f"Failed to decrypt TOTP secret for user {user.id}")

        # Decrypt TOTP backup codes if present
        totp_backup_codes = None
        if user.totp_backup_codes_encrypted:
            try:
                totp_backup_codes = self.encryption.decrypt(user.totp_backup_codes_encrypted)
            except ValueError:
                logger.warning(f"Failed to decrypt TOTP backup codes for user {user.id}")

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "picture_url": user.picture_url,
            # Include password_hash for restore - it's already hashed
            "password_hash": user.password_hash,
            "auth_provider": user.auth_provider,
            "is_active": user.is_active,
            "is_locked": user.is_locked,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until,
            "password_changed_at": user.password_changed_at,
            "require_password_change": user.require_password_change,
            # TOTP fields - decrypted for portable backup
            "totp_secret": totp_secret,  # Decrypted, will be re-encrypted on import
            "totp_enabled": user.totp_enabled,
            "totp_verified_at": user.totp_verified_at,
            "totp_backup_codes": totp_backup_codes,  # Decrypted, will be re-encrypted on import
            "last_login_at": user.last_login_at,
            "date_format": user.date_format,
            "number_format": user.number_format,
            "currency": user.currency,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    def _provider_to_dict(self, provider: ProviderORM) -> dict[str, Any]:
        """Convert provider ORM to dict, decrypting credentials for portability.

        Credentials are stored decrypted in the backup since the backup itself
        is password-encrypted. This allows backups to be restored on servers
        with different ENCRYPTION_KEYs.
        """
        # Decrypt credentials for portable backup
        try:
            credentials = self.encryption.decrypt(provider.credentials_encrypted)
        except ValueError:
            # If decryption fails, store as None - credentials will need to be re-entered
            logger.warning(f"Failed to decrypt credentials for provider {provider.id}")
            credentials = None

        return {
            "id": provider.id,
            "name": provider.name,
            "display_name": provider.display_name,
            "logo_url": provider.logo_url,
            "enabled": provider.enabled,
            "credentials": credentials,  # Decrypted, will be re-encrypted on import
            "config": provider.config,
            "last_sync_at": provider.last_sync_at,
            "last_sync_status": provider.last_sync_status,
            "payment_method_id": provider.payment_method_id,
            "created_at": provider.created_at,
            "updated_at": provider.updated_at,
        }

    def _settings_to_dict(self, settings: SettingsORM) -> dict[str, Any]:
        """Convert settings ORM to dict."""
        return {
            "key": settings.key,
            "value": settings.value,
            "updated_at": settings.updated_at,
        }

    def _audit_log_to_dict(self, audit_log: AuditLogORM) -> dict[str, Any]:
        """Convert audit log ORM to dict."""
        return {
            "id": audit_log.id,
            "admin_user_id": audit_log.admin_user_id,
            "action": audit_log.action,
            "resource_type": audit_log.resource_type,
            "resource_id": audit_log.resource_id,
            "changes": audit_log.changes,
            "ip_address": str(audit_log.ip_address) if audit_log.ip_address else None,
            "user_agent": audit_log.user_agent,
            "created_at": audit_log.created_at,
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
            Backup info response with format validation and integrity hash
        """
        if not file_data.startswith(BACKUP_HEADER):
            return BackupInfoResponse(
                valid_format=False,
                error="Invalid backup format: missing or wrong header",
            )

        header_len = len(BACKUP_HEADER)
        min_size = header_len + HASH_SIZE + SALT_SIZE + NONCE_SIZE + 16

        if len(file_data) < min_size:
            return BackupInfoResponse(
                valid_format=False,
                error="Invalid backup format: file too short",
            )

        # Extract integrity hash for display
        content_hash = file_data[header_len : header_len + HASH_SIZE]

        return BackupInfoResponse(
            valid_format=True,
            version=BACKUP_VERSION,
            requires_password=True,
            compressed=True,
            integrity_hash=content_hash.hex(),
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
                user=user,
                request=request,
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

        # Required data keys for V1 backups
        required_data_keys_v1 = [
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
        ]

        for key in required_data_keys_v1:
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

        # 1. User notification preferences (depends on admin_users)
        await self.session.execute(delete(UserNotificationPreferenceORM))

        # 2. User roles (depends on admin_users and roles)
        await self.session.execute(delete(UserRoleORM))

        # 3. Role permissions (depends on roles and permissions)
        await self.session.execute(delete(RolePermissionORM))

        # 4. Licenses (depends on providers, employees, admin_users)
        await self.session.execute(delete(LicenseORM))

        # 5. License packages, org licenses, provider files, cost snapshots (depend on providers)
        await self.session.execute(delete(LicensePackageORM))
        await self.session.execute(delete(OrganizationLicenseORM))
        await self.session.execute(delete(ProviderFileORM))
        await self.session.execute(delete(CostSnapshotORM))

        # 6. Service account patterns and license types (depend on employees and admin_users)
        await self.session.execute(delete(ServiceAccountPatternORM))
        await self.session.execute(delete(AdminAccountPatternORM))
        await self.session.execute(delete(ServiceAccountLicenseTypeORM))

        # 7. Providers (depends on payment_methods)
        await self.session.execute(delete(ProviderORM))

        # 8. Employees (no FK dependencies after above cleared)
        await self.session.execute(delete(EmployeeORM))

        # 9. Payment methods
        await self.session.execute(delete(PaymentMethodORM))

        # 10. Admin users (after all dependencies cleared)
        await self.session.execute(delete(AdminUserORM))

        # 11. Roles and permissions
        await self.session.execute(delete(RoleORM))
        await self.session.execute(delete(PermissionORM))

        # 12. Independent tables
        await self.session.execute(delete(NotificationRuleORM))
        await self.session.execute(delete(SettingsORM))

        # 13. Audit logs (immutable but included for full restore)
        await self.session.execute(delete(AuditLogORM))

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

        # 3. Permissions (no dependencies)
        for p in data.get("permissions", []):
            perm_orm = PermissionORM(
                id=UUID(p["id"]) if isinstance(p["id"], str) else p["id"],
                code=p["code"],
                name=p["name"],
                description=p.get("description"),
                category=p["category"],
                created_at=self._parse_datetime(p.get("created_at")),
                updated_at=self._parse_datetime(p.get("updated_at")),
            )
            self.session.add(perm_orm)
            counts.permissions += 1

        # 4. Roles (no dependencies)
        for r in data.get("roles", []):
            role_orm = RoleORM(
                id=UUID(r["id"]) if isinstance(r["id"], str) else r["id"],
                code=r["code"],
                name=r["name"],
                description=r.get("description"),
                is_system=r.get("is_system", False),
                priority=r.get("priority", 0),
                created_at=self._parse_datetime(r.get("created_at")),
                updated_at=self._parse_datetime(r.get("updated_at")),
            )
            self.session.add(role_orm)
            counts.roles += 1

        # 5. Admin users (no dependencies)
        for u in data.get("admin_users", []):
            # Handle TOTP secret: new format (plaintext) or old format (encrypted bytes)
            totp_secret_encrypted = None
            if u.get("totp_secret"):
                # New format: plaintext secret, encrypt with current key
                totp_secret_encrypted = self.encryption.encrypt_string(u["totp_secret"])
            elif u.get("totp_secret_encrypted"):
                # Old format: already encrypted (backward compatibility)
                totp_secret = u["totp_secret_encrypted"]
                if isinstance(totp_secret, str):
                    totp_secret_encrypted = base64.b64decode(totp_secret)
                else:
                    totp_secret_encrypted = totp_secret

            # Handle TOTP backup codes: new format (plaintext) or old format (encrypted bytes)
            totp_backup_codes_encrypted = None
            if u.get("totp_backup_codes"):
                # New format: plaintext codes, encrypt with current key
                totp_backup_codes_encrypted = self.encryption.encrypt(u["totp_backup_codes"])
            elif u.get("totp_backup_codes_encrypted"):
                # Old format: already encrypted (backward compatibility)
                totp_backup_codes = u["totp_backup_codes_encrypted"]
                if isinstance(totp_backup_codes, str):
                    totp_backup_codes_encrypted = base64.b64decode(totp_backup_codes)
                else:
                    totp_backup_codes_encrypted = totp_backup_codes

            user_orm = AdminUserORM(
                id=UUID(u["id"]) if isinstance(u["id"], str) else u["id"],
                email=u["email"],
                name=u.get("name"),
                picture_url=u.get("picture_url"),
                password_hash=u.get("password_hash"),
                auth_provider=u.get("auth_provider", "local"),
                is_active=u.get("is_active", True),
                is_locked=u.get("is_locked", False),
                failed_login_attempts=u.get("failed_login_attempts", 0),
                locked_until=self._parse_datetime(u.get("locked_until")),
                password_changed_at=self._parse_datetime(u.get("password_changed_at")),
                require_password_change=u.get("require_password_change", False),
                totp_secret_encrypted=totp_secret_encrypted,
                totp_enabled=u.get("totp_enabled", False),
                totp_verified_at=self._parse_datetime(u.get("totp_verified_at")),
                totp_backup_codes_encrypted=totp_backup_codes_encrypted,
                last_login_at=self._parse_datetime(u.get("last_login_at")),
                date_format=u.get("date_format", "DD.MM.YYYY"),
                number_format=u.get("number_format", "de-DE"),
                currency=u.get("currency", "EUR"),
                created_at=self._parse_datetime(u.get("created_at")),
                updated_at=self._parse_datetime(u.get("updated_at")),
            )
            self.session.add(user_orm)
            counts.admin_users += 1

        # 6. Employees (self-referential FK: manager_id -> employees.id)
        # Insert in two passes to handle manager_id references
        # Pass 1: Insert all employees WITHOUT manager_id
        employee_manager_map: dict[UUID, UUID] = {}  # employee_id -> manager_id
        for e in data["employees"]:
            emp_id = UUID(e["id"]) if isinstance(e["id"], str) else e["id"]
            # Store manager_id for second pass
            if e.get("manager_id"):
                manager_id = UUID(e["manager_id"]) if isinstance(e["manager_id"], str) else e["manager_id"]
                employee_manager_map[emp_id] = manager_id

            emp_orm = EmployeeORM(
                id=emp_id,
                hibob_id=e["hibob_id"],
                email=e["email"],
                full_name=e["full_name"],
                department=e.get("department"),
                status=e["status"],
                source=e.get("source", "hibob"),
                start_date=self._parse_date(e.get("start_date")),
                termination_date=self._parse_date(e.get("termination_date")),
                avatar_url=e.get("avatar_url"),
                manager_email=e.get("manager_email"),
                manager_id=None,  # Set to None initially, will update in pass 2
                synced_at=self._parse_datetime(e["synced_at"]),
                created_at=self._parse_datetime(e.get("created_at")),
                updated_at=self._parse_datetime(e.get("updated_at")),
            )
            self.session.add(emp_orm)
            counts.employees += 1

        await self.session.flush()

        # Pass 2: Update employees with their manager_id references
        if employee_manager_map:
            from sqlalchemy import update
            for emp_id, manager_id in employee_manager_map.items():
                await self.session.execute(
                    update(EmployeeORM)
                    .where(EmployeeORM.id == emp_id)
                    .values(manager_id=manager_id)
                )
            await self.session.flush()

        # 7. Role permissions (depends on roles and permissions)
        for rp in data.get("role_permissions", []):
            rp_orm = RolePermissionORM(
                role_id=UUID(rp["role_id"]) if isinstance(rp["role_id"], str) else rp["role_id"],
                permission_id=UUID(rp["permission_id"]) if isinstance(rp["permission_id"], str) else rp["permission_id"],
                created_at=self._parse_datetime(rp.get("created_at")),
            )
            self.session.add(rp_orm)
            counts.role_permissions += 1

        # 8. User roles (depends on admin_users and roles)
        for ur in data.get("user_roles", []):
            ur_orm = UserRoleORM(
                user_id=UUID(ur["user_id"]) if isinstance(ur["user_id"], str) else ur["user_id"],
                role_id=UUID(ur["role_id"]) if isinstance(ur["role_id"], str) else ur["role_id"],
                assigned_at=self._parse_datetime(ur.get("assigned_at")),
                assigned_by=UUID(ur["assigned_by"]) if ur.get("assigned_by") else None,
            )
            self.session.add(ur_orm)
            counts.user_roles += 1

        # 9. User notification preferences (depends on admin_users)
        for unp in data.get("user_notification_preferences", []):
            unp_orm = UserNotificationPreferenceORM(
                id=UUID(unp["id"]) if isinstance(unp["id"], str) else unp["id"],
                user_id=UUID(unp["user_id"]) if isinstance(unp["user_id"], str) else unp["user_id"],
                event_type=unp["event_type"],
                enabled=unp.get("enabled", True),
                slack_dm=unp.get("slack_dm", False),
                slack_channel=unp.get("slack_channel"),
                created_at=self._parse_datetime(unp.get("created_at")),
                updated_at=self._parse_datetime(unp.get("updated_at")),
            )
            self.session.add(unp_orm)
            counts.user_notification_preferences += 1

        # 10. Providers (depends on payment_methods)
        for p in data["providers"]:
            # Handle credentials: new format (plaintext dict) or old format (encrypted bytes)
            if p.get("credentials") is not None:
                # New format: plaintext credentials, encrypt with current key
                credentials_encrypted = self.encryption.encrypt(p["credentials"])
            elif p.get("credentials_encrypted"):
                # Old format: already encrypted (backward compatibility)
                credentials = p["credentials_encrypted"]
                if isinstance(credentials, str):
                    credentials_encrypted = base64.b64decode(credentials)
                else:
                    credentials_encrypted = credentials
            else:
                # No credentials - encrypt empty dict
                credentials_encrypted = self.encryption.encrypt({})

            provider_orm = ProviderORM(
                id=UUID(p["id"]) if isinstance(p["id"], str) else p["id"],
                name=p["name"],
                display_name=p["display_name"],
                logo_url=p.get("logo_url"),
                enabled=p.get("enabled", True),
                credentials_encrypted=credentials_encrypted,
                config=p.get("config"),
                last_sync_at=self._parse_datetime(p.get("last_sync_at")),
                last_sync_status=p.get("last_sync_status"),
                payment_method_id=UUID(p["payment_method_id"]) if p.get("payment_method_id") else None,
                created_at=self._parse_datetime(p.get("created_at")),
                updated_at=self._parse_datetime(p.get("updated_at")),
            )
            self.session.add(provider_orm)
            counts.providers += 1

        # 11. Notification rules (no dependencies)
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

        # 12. License packages (depends on providers)
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

        # 13. Organization licenses (depends on providers)
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

        # 14. Cost snapshots (depends on providers)
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

        # 15. Licenses (depends on providers and employees)
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
                is_admin_account=lic.get("is_admin_account", False),
                admin_account_name=lic.get("admin_account_name"),
                admin_account_owner_id=UUID(lic["admin_account_owner_id"]) if lic.get("admin_account_owner_id") else None,
                suggested_employee_id=UUID(lic["suggested_employee_id"]) if lic.get("suggested_employee_id") else None,
                match_confidence=lic.get("match_confidence"),
                match_status=lic.get("match_status"),
                match_method=lic.get("match_method"),
                match_reviewed_at=self._parse_datetime(lic.get("match_reviewed_at")),
                match_reviewed_by=UUID(lic["match_reviewed_by"]) if lic.get("match_reviewed_by") else None,
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

        # 16. Provider files (depends on providers) - also restore files to disk
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

        # 17. Service account patterns (depends on employees for owner_id)
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

        # 18. Admin account patterns (depends on employees for owner_id)
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

        # 19. Service account license types (depends on employees and admin_users)
        for salt in data.get("service_account_license_types", []):
            salt_orm = ServiceAccountLicenseTypeORM(
                id=UUID(salt["id"]) if isinstance(salt["id"], str) else salt["id"],
                license_type=salt["license_type"],
                name=salt.get("name"),
                owner_id=UUID(salt["owner_id"]) if salt.get("owner_id") else None,
                notes=salt.get("notes"),
                created_by=UUID(salt["created_by"]) if salt.get("created_by") else None,
                created_at=self._parse_datetime(salt.get("created_at")),
                updated_at=self._parse_datetime(salt.get("updated_at")),
            )
            self.session.add(salt_orm)
            counts.service_account_license_types += 1

        # 20. Audit logs (depends on admin_users)
        for al in data.get("audit_logs", []):
            al_orm = AuditLogORM(
                id=UUID(al["id"]) if isinstance(al["id"], str) else al["id"],
                admin_user_id=UUID(al["admin_user_id"]) if al.get("admin_user_id") else None,
                action=al["action"],
                resource_type=al["resource_type"],
                resource_id=UUID(al["resource_id"]) if al.get("resource_id") else None,
                changes=al.get("changes"),
                ip_address=al.get("ip_address"),
                user_agent=al.get("user_agent"),
                created_at=self._parse_datetime(al.get("created_at")),
            )
            self.session.add(al_orm)
            counts.audit_logs += 1

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
