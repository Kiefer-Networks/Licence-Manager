"""Import service for license imports from CSV files."""

import logging
import os
import tempfile
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.dto.import_dto import (
    CSVOptions,
    ImportExecuteRequest,
    ImportExecuteResponse,
    ImportJobStatus,
    ImportOptions,
    ImportPreviewRow,
    ImportResult,
    ImportRowError,
    ImportRowWarning,
    ImportSummary,
    ImportUploadResponse,
    ImportValidateRequest,
    ImportValidateResponse,
)
from licence_api.models.orm.import_job import ImportJobORM
from licence_api.models.orm.license import LicenseORM
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.repositories.provider_repository import ProviderRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.utils.file_parser import (
    parse_boolean,
    parse_csv_file,
    parse_date,
    suggest_column_mapping,
    validate_email,
)

logger = logging.getLogger(__name__)

# Maximum file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024
# Maximum rows to import
MAX_IMPORT_ROWS = 1000
# Upload temp directory
UPLOAD_DIR = os.path.join(tempfile.gettempdir(), "licence_imports")

# System fields that can be mapped
SYSTEM_FIELDS = [
    "license_key",
    "external_user_id",
    "license_type",
    "employee_email",
    "monthly_cost",
    "currency",
    "valid_until",
    "status",
    "notes",
    "is_service_account",
    "service_account_name",
    "is_admin_account",
    "admin_account_name",
]

# Required fields (at least one of these)
REQUIRED_FIELDS = ["license_key", "external_user_id"]


class ImportService:
    """Service for importing licenses from CSV files."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self.session = session
        self.license_repo = LicenseRepository(session)
        self.employee_repo = EmployeeRepository(session)
        self.provider_repo = ProviderRepository(session)
        self.audit_service = AuditService(session)

    async def upload_file(
        self,
        provider_id: UUID,
        file: UploadFile,
        user: AdminUser,
    ) -> ImportUploadResponse:
        """Upload and analyze a CSV file for import.

        Args:
            provider_id: Provider UUID
            file: Uploaded file
            user: Current admin user

        Returns:
            ImportUploadResponse with file analysis

        Raises:
            ValueError: If file is invalid
        """
        # Validate provider exists
        provider = await self.provider_repo.get_by_id(provider_id)
        if provider is None:
            raise ValueError("Provider not found")

        # Validate file extension
        if not file.filename:
            raise ValueError("Filename is required")

        filename_lower = file.filename.lower()
        if not filename_lower.endswith(".csv"):
            raise ValueError("Only CSV files are supported")

        # Read file content
        content = await file.read()
        file_size = len(content)

        if file_size == 0:
            raise ValueError("File is empty")

        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)} MB")

        # Parse the file
        try:
            parsed = parse_csv_file(content, max_rows=MAX_IMPORT_ROWS)
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {str(e)}")

        if parsed["total_rows"] > MAX_IMPORT_ROWS:
            raise ValueError(
                f"File has too many rows ({parsed['total_rows']}). Maximum is {MAX_IMPORT_ROWS}"
            )

        # Generate upload ID
        upload_id = uuid4()

        # Save file to temp directory
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(UPLOAD_DIR, f"{upload_id}.csv")
        with open(file_path, "wb") as f:
            f.write(content)

        # Suggest column mapping
        suggested_mapping = suggest_column_mapping(parsed["columns"])

        # Get preview (first 5 rows)
        preview = parsed["rows"][:5] if parsed["rows"] else []

        return ImportUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            file_size=file_size,
            detected_encoding=parsed["encoding"],
            detected_delimiter=parsed["delimiter"],
            row_count=parsed["total_rows"],
            columns=parsed["columns"],
            suggested_mapping=suggested_mapping,
            preview=preview,
        )

    async def validate_import(
        self,
        provider_id: UUID,
        request: ImportValidateRequest,
        user: AdminUser,
    ) -> ImportValidateResponse:
        """Validate import data and return preview.

        Args:
            provider_id: Provider UUID
            request: Validation request with mapping
            user: Current admin user

        Returns:
            ImportValidateResponse with validation results

        Raises:
            ValueError: If upload not found or validation fails
        """
        # Load uploaded file
        file_path = os.path.join(UPLOAD_DIR, f"{request.upload_id}.csv")
        if not os.path.exists(file_path):
            raise ValueError("Upload not found or expired")

        with open(file_path, "rb") as f:
            content = f.read()

        # Parse file with options
        csv_options = request.options.csv_options or CSVOptions()
        parsed = parse_csv_file(
            content,
            delimiter=csv_options.delimiter,
            encoding=csv_options.encoding,
            has_header=csv_options.has_header,
            skip_rows=csv_options.skip_rows,
            max_rows=MAX_IMPORT_ROWS,
        )

        # Build mapping dict
        mapping: dict[str, str | None] = {}
        for col_map in request.column_mapping:
            mapping[col_map.file_column] = col_map.system_field

        # Check if at least one required field is mapped
        mapped_fields = set(mapping.values())
        if not any(f in mapped_fields for f in REQUIRED_FIELDS):
            raise ValueError(f"At least one of {', '.join(REQUIRED_FIELDS)} must be mapped")

        # Get existing external_user_ids for duplicate detection
        existing_ids = await self._get_existing_external_ids(provider_id)

        # Collect all employee emails for batch lookup
        email_field = None
        for col, field in mapping.items():
            if field == "employee_email":
                email_field = col
                break

        employee_map: dict[str, Any] = {}
        if email_field:
            emails = [
                row.get(email_field, "").lower() for row in parsed["rows"] if row.get(email_field)
            ]
            if emails:
                employee_map = await self.employee_repo.get_by_emails(emails)

        # Validate each row
        errors: list[ImportRowError] = []
        warnings: list[ImportRowWarning] = []
        preview_rows: list[ImportPreviewRow] = []

        valid_count = 0
        will_create = 0
        will_skip_duplicates = 0
        will_skip_errors = 0
        employees_matched = 0
        employees_not_found = 0
        seen_keys: set[str] = set()

        for row_num, row in enumerate(parsed["rows"], start=1):
            row_errors: list[ImportRowError] = []
            row_warnings: list[ImportRowWarning] = []

            # Extract mapped values
            mapped_row: dict[str, Any] = {}
            for col, field in mapping.items():
                if field:
                    mapped_row[field] = row.get(col, "")

            # Get license key
            license_key = (
                mapped_row.get("license_key", "").strip()
                or mapped_row.get("external_user_id", "").strip()
            )

            if not license_key:
                row_errors.append(
                    ImportRowError(
                        row=row_num,
                        column="license_key",
                        value="",
                        message="License key or external user ID is required",
                        code="MISSING_REQUIRED",
                    )
                )
            else:
                # Check for duplicate in file
                if license_key in seen_keys:
                    row_warnings.append(
                        ImportRowWarning(
                            row=row_num,
                            column="license_key",
                            value=license_key,
                            message="Duplicate key in file",
                            code="DUPLICATE_IN_FILE",
                        )
                    )
                seen_keys.add(license_key)

                # Check for duplicate in database
                if license_key in existing_ids:
                    row_warnings.append(
                        ImportRowWarning(
                            row=row_num,
                            column="license_key",
                            value=license_key,
                            message="License already exists",
                            code="DUPLICATE_IN_DB",
                        )
                    )
                    will_skip_duplicates += 1

            # Validate email if provided
            employee_email = mapped_row.get("employee_email", "").strip()
            if employee_email:
                if not validate_email(employee_email):
                    row_errors.append(
                        ImportRowError(
                            row=row_num,
                            column="employee_email",
                            value=employee_email,
                            message="Invalid email format",
                            code="INVALID_EMAIL",
                        )
                    )
                else:
                    # Check if employee exists
                    if employee_email.lower() in employee_map:
                        employees_matched += 1
                    else:
                        employees_not_found += 1
                        row_warnings.append(
                            ImportRowWarning(
                                row=row_num,
                                column="employee_email",
                                value=employee_email,
                                message="Employee not found in system",
                                code="EMPLOYEE_NOT_FOUND",
                            )
                        )

            # Validate monthly_cost
            monthly_cost = mapped_row.get("monthly_cost", "").strip()
            if monthly_cost:
                try:
                    cost = Decimal(monthly_cost.replace(",", "."))
                    if cost < 0:
                        row_errors.append(
                            ImportRowError(
                                row=row_num,
                                column="monthly_cost",
                                value=monthly_cost,
                                message="Cost cannot be negative",
                                code="INVALID_COST",
                            )
                        )
                except InvalidOperation:
                    row_errors.append(
                        ImportRowError(
                            row=row_num,
                            column="monthly_cost",
                            value=monthly_cost,
                            message="Invalid number format",
                            code="INVALID_NUMBER",
                        )
                    )

            # Validate date
            valid_until = mapped_row.get("valid_until", "").strip()
            if valid_until:
                parsed_date = parse_date(valid_until)
                if parsed_date is None:
                    row_errors.append(
                        ImportRowError(
                            row=row_num,
                            column="valid_until",
                            value=valid_until,
                            message="Invalid date format",
                            code="INVALID_DATE",
                        )
                    )

            # Validate status
            status = mapped_row.get("status", "").strip().lower()
            if status and status not in ("active", "inactive", "suspended"):
                row_errors.append(
                    ImportRowError(
                        row=row_num,
                        column="status",
                        value=status,
                        message="Invalid status. Must be: active, inactive, or suspended",
                        code="INVALID_STATUS",
                    )
                )

            # Build preview row
            has_errors = len(row_errors) > 0
            has_warnings = len(row_warnings) > 0

            status_str = "valid"
            if has_errors:
                status_str = "error"
                will_skip_errors += 1
            elif has_warnings:
                status_str = "warning"
                if license_key not in existing_ids:
                    will_create += 1
            else:
                will_create += 1
                valid_count += 1

            preview_rows.append(
                ImportPreviewRow(
                    row_number=row_num,
                    data=mapped_row,
                    has_errors=has_errors,
                    has_warnings=has_warnings,
                    status=status_str,
                )
            )

            errors.extend(row_errors)
            warnings.extend(row_warnings)

        # Build summary
        summary = ImportSummary(
            will_create=will_create,
            will_skip_duplicates=will_skip_duplicates,
            will_skip_errors=will_skip_errors,
            employees_matched=employees_matched,
            employees_not_found=employees_not_found,
        )

        return ImportValidateResponse(
            is_valid=len(errors) == 0,
            can_proceed=len(errors) == 0 or request.options.error_handling == "skip",
            total_rows=len(parsed["rows"]),
            valid_rows=valid_count,
            error_count=len(errors),
            warning_count=len(warnings),
            errors=errors[:100],  # Limit to first 100 errors
            warnings=warnings[:100],  # Limit to first 100 warnings
            preview=preview_rows[:20],  # Limit preview to 20 rows
            summary=summary,
        )

    async def execute_import(
        self,
        provider_id: UUID,
        request: ImportExecuteRequest,
        user: AdminUser,
        http_request: Request | None = None,
    ) -> ImportExecuteResponse:
        """Execute the import and create licenses.

        Args:
            provider_id: Provider UUID
            request: Import execution request
            user: Current admin user
            http_request: HTTP request for audit logging

        Returns:
            ImportExecuteResponse with job ID

        Raises:
            ValueError: If import fails
        """
        # Load uploaded file
        file_path = os.path.join(UPLOAD_DIR, f"{request.upload_id}.csv")
        if not os.path.exists(file_path):
            raise ValueError("Upload not found or expired")

        with open(file_path, "rb") as f:
            content = f.read()

        # Get file info
        file_size = len(content)
        filename = f"import_{request.upload_id}.csv"

        # Parse file with options
        csv_options = request.options.csv_options or CSVOptions()
        parsed = parse_csv_file(
            content,
            delimiter=csv_options.delimiter,
            encoding=csv_options.encoding,
            has_header=csv_options.has_header,
            skip_rows=csv_options.skip_rows,
            max_rows=MAX_IMPORT_ROWS,
        )

        # Build mapping dict
        mapping: dict[str, str | None] = {}
        for col_map in request.column_mapping:
            mapping[col_map.file_column] = col_map.system_field

        # Create import job record
        job = ImportJobORM(
            provider_id=provider_id,
            status="processing",
            filename=filename,
            file_size=file_size,
            total_rows=len(parsed["rows"]),
            column_mapping=[m.model_dump() for m in request.column_mapping],
            options=request.options.model_dump(),
            started_at=datetime.now(UTC),
            created_by=user.id,
        )
        self.session.add(job)
        await self.session.flush()

        # Get existing external_user_ids
        existing_ids = await self._get_existing_external_ids(provider_id)

        # Get employee map for matching
        email_field = None
        for col, field in mapping.items():
            if field == "employee_email":
                email_field = col
                break

        employee_map: dict[str, Any] = {}
        if email_field:
            emails = [
                row.get(email_field, "").lower() for row in parsed["rows"] if row.get(email_field)
            ]
            if emails:
                employee_map = await self.employee_repo.get_by_emails(emails)

        # Process each row
        created = 0
        skipped = 0
        error_count = 0
        error_details: list[dict] = []

        for row_num, row in enumerate(parsed["rows"], start=1):
            try:
                result = await self._process_row(
                    provider_id=provider_id,
                    row=row,
                    row_num=row_num,
                    mapping=mapping,
                    existing_ids=existing_ids,
                    employee_map=employee_map,
                    options=request.options,
                )

                if result == "created":
                    created += 1
                elif result == "skipped":
                    skipped += 1

                job.processed_rows = row_num

            except Exception as e:
                error_count += 1
                error_details.append(
                    {
                        "row": row_num,
                        "message": str(e),
                    }
                )

                if request.options.error_handling == "strict":
                    job.status = "failed"
                    job.error_details = {"errors": error_details}
                    await self.session.commit()
                    raise ValueError(f"Import failed at row {row_num}: {str(e)}")

        # Update job status
        job.status = "completed"
        job.created_count = created
        job.skipped_count = skipped
        job.error_count = error_count
        job.completed_at = datetime.now(UTC)
        job.error_details = {"errors": error_details} if error_details else None

        # Audit log
        await self.audit_service.log(
            action=AuditAction.LICENSE_BULK_CREATE,
            resource_type=ResourceType.LICENSE,
            resource_id=provider_id,
            user=user,
            request=http_request,
            details={
                "job_id": str(job.id),
                "total_rows": len(parsed["rows"]),
                "created": created,
                "skipped": skipped,
                "errors": error_count,
            },
        )

        await self.session.commit()

        # Clean up temp file
        try:
            os.remove(file_path)
        except OSError:
            pass

        return ImportExecuteResponse(
            job_id=job.id,
            status=job.status,
        )

    async def get_job_status(
        self,
        provider_id: UUID,
        job_id: UUID,
    ) -> ImportJobStatus | None:
        """Get import job status.

        Args:
            provider_id: Provider UUID
            job_id: Import job UUID

        Returns:
            ImportJobStatus or None if not found
        """
        from sqlalchemy import select

        result = await self.session.execute(
            select(ImportJobORM).where(
                ImportJobORM.id == job_id,
                ImportJobORM.provider_id == provider_id,
            )
        )
        job = result.scalar_one_or_none()

        if job is None:
            return None

        # Build result
        result_data = None
        if job.status == "completed":
            result_data = ImportResult(
                created=job.created_count,
                skipped=job.skipped_count,
                errors=job.error_count,
                error_details=[
                    ImportRowError(
                        row=e.get("row", 0),
                        column="",
                        value="",
                        message=e.get("message", ""),
                        code="PROCESSING_ERROR",
                    )
                    for e in (job.error_details or {}).get("errors", [])
                ],
            )

        progress = 0
        if job.total_rows > 0:
            progress = int((job.processed_rows / job.total_rows) * 100)

        return ImportJobStatus(
            job_id=job.id,
            provider_id=job.provider_id,
            status=job.status,
            progress=progress,
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            created=job.created_count,
            skipped=job.skipped_count,
            errors=job.error_count,
            started_at=job.started_at,
            completed_at=job.completed_at,
            result=result_data,
        )

    async def generate_template(
        self,
        provider_id: UUID,
        include_examples: bool = True,
    ) -> str:
        """Generate a CSV template for imports.

        Args:
            provider_id: Provider UUID
            include_examples: Whether to include example rows

        Returns:
            CSV content as string
        """
        # Build header
        columns = [
            "license_key",
            "license_type",
            "employee_email",
            "monthly_cost",
            "currency",
            "valid_until",
            "status",
            "notes",
            "is_service_account",
            "service_account_name",
        ]

        lines = [",".join(columns)]

        if include_examples:
            # Add example rows
            lines.append(
                "LIC-001,Professional,max.mustermann@example.com,"
                "99.00,EUR,2025-12-31,active,Main license,false,"
            )
            lines.append(
                "LIC-002,Enterprise,anna.schmidt@example.com,199.00,EUR,2025-12-31,active,,false,"
            )
            lines.append("SVC-001,API,,,EUR,,active,API Access,true,API Bot")

        return "\n".join(lines)

    async def _get_existing_external_ids(self, provider_id: UUID) -> set[str]:
        """Get all existing external_user_ids for a provider.

        Args:
            provider_id: Provider UUID

        Returns:
            Set of existing external_user_ids
        """
        from sqlalchemy import select

        result = await self.session.execute(
            select(LicenseORM.external_user_id).where(LicenseORM.provider_id == provider_id)
        )
        return {row[0] for row in result.all()}

    async def _process_row(
        self,
        provider_id: UUID,
        row: dict[str, str],
        row_num: int,
        mapping: dict[str, str | None],
        existing_ids: set[str],
        employee_map: dict[str, Any],
        options: ImportOptions,
    ) -> str:
        """Process a single import row.

        Args:
            provider_id: Provider UUID
            row: Row data
            row_num: Row number (for error messages)
            mapping: Column to field mapping
            existing_ids: Set of existing external_user_ids
            employee_map: Map of email -> employee
            options: Import options

        Returns:
            "created" or "skipped"
        """
        # Extract mapped values
        mapped: dict[str, Any] = {}
        for col, field in mapping.items():
            if field:
                mapped[field] = row.get(col, "").strip()

        # Get external_user_id (license key)
        external_user_id = mapped.get("license_key", "") or mapped.get("external_user_id", "")

        if not external_user_id:
            raise ValueError("Missing license key or external user ID")

        # Skip duplicates
        if external_user_id in existing_ids:
            return "skipped"

        # Parse values
        license_type = mapped.get("license_type", None)
        status = mapped.get("status", options.default_status) or options.default_status
        notes = mapped.get("notes", None) or None
        currency = mapped.get("currency", options.default_currency) or options.default_currency

        # Parse cost
        monthly_cost = None
        cost_str = mapped.get("monthly_cost", "")
        if cost_str:
            try:
                monthly_cost = Decimal(cost_str.replace(",", "."))
            except InvalidOperation:
                pass

        # Parse date
        expires_at = None
        date_str = mapped.get("valid_until", "")
        if date_str:
            parsed_date = parse_date(date_str)
            if parsed_date:
                from datetime import date

                year, month, day = parsed_date.split("-")
                expires_at = date(int(year), int(month), int(day))

        # Parse service account flags
        is_service_account = parse_boolean(mapped.get("is_service_account", "")) or False
        service_account_name = mapped.get("service_account_name", None) or None
        is_admin_account = parse_boolean(mapped.get("is_admin_account", "")) or False
        admin_account_name = mapped.get("admin_account_name", None) or None

        # Match employee
        employee_id = None
        employee_email = mapped.get("employee_email", "").lower()
        if employee_email and employee_email in employee_map:
            employee_id = employee_map[employee_email].id

        # Create license
        license_orm = LicenseORM(
            provider_id=provider_id,
            external_user_id=external_user_id,
            license_type=license_type,
            status=status,
            employee_id=employee_id,
            monthly_cost=monthly_cost,
            currency=currency,
            expires_at=expires_at,
            is_service_account=is_service_account,
            service_account_name=service_account_name,
            is_admin_account=is_admin_account,
            admin_account_name=admin_account_name,
            synced_at=datetime.now(UTC),
            extra_data={"notes": notes} if notes else None,
        )
        self.session.add(license_orm)

        # Add to existing_ids to prevent duplicates in same batch
        existing_ids.add(external_user_id)

        return "created"
