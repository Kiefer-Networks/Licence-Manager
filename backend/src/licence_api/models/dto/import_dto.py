"""Import DTOs for license import system."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CSVOptions(BaseModel):
    """CSV parsing options."""

    delimiter: str = ","
    encoding: str = "utf-8"
    has_header: bool = True
    skip_rows: int = 0
    quote_char: str = '"'


class ImportColumnMapping(BaseModel):
    """Mapping from file column to system field."""

    file_column: str
    system_field: str | None = None  # None = ignore column


class ImportOptions(BaseModel):
    """Import execution options."""

    error_handling: Literal["strict", "skip"] = "skip"
    csv_options: CSVOptions | None = None
    default_status: str = "active"
    default_currency: str = "EUR"


class ImportUploadResponse(BaseModel):
    """Response after file upload with auto-detection results."""

    upload_id: UUID
    filename: str
    file_size: int
    detected_encoding: str
    detected_delimiter: str
    row_count: int
    columns: list[str]
    suggested_mapping: dict[str, str | None]  # file_column -> system_field
    preview: list[dict[str, str]]  # First 5 rows as dict


class ImportRowError(BaseModel):
    """Error in a specific row."""

    row: int
    column: str
    value: str
    message: str
    code: str  # e.g. "INVALID_EMAIL", "MISSING_REQUIRED"


class ImportRowWarning(BaseModel):
    """Warning for a specific row."""

    row: int
    column: str | None = None
    value: str | None = None
    message: str
    code: str  # e.g. "DUPLICATE_IN_DB", "EMPLOYEE_NOT_FOUND"


class ImportPreviewRow(BaseModel):
    """Preview of a row to be imported."""

    row_number: int
    data: dict[str, Any]
    has_errors: bool = False
    has_warnings: bool = False
    status: str = "valid"  # valid, error, warning, skipped


class ImportSummary(BaseModel):
    """Summary of import validation."""

    will_create: int
    will_skip_duplicates: int
    will_skip_errors: int
    employees_matched: int
    employees_not_found: int


class ImportValidateRequest(BaseModel):
    """Request to validate import data."""

    upload_id: UUID
    column_mapping: list[ImportColumnMapping]
    options: ImportOptions = Field(default_factory=ImportOptions)


class ImportValidateResponse(BaseModel):
    """Response from import validation."""

    is_valid: bool  # True if no errors
    can_proceed: bool  # True if only warnings or no issues
    total_rows: int
    valid_rows: int
    error_count: int
    warning_count: int
    errors: list[ImportRowError]
    warnings: list[ImportRowWarning]
    preview: list[ImportPreviewRow]
    summary: ImportSummary


class ImportExecuteRequest(BaseModel):
    """Request to execute import."""

    upload_id: UUID
    column_mapping: list[ImportColumnMapping]
    options: ImportOptions = Field(default_factory=ImportOptions)
    confirmed: bool = False  # Must be true if there are warnings


class ImportExecuteResponse(BaseModel):
    """Response after import execution."""

    job_id: UUID
    status: str  # pending, processing, completed, failed


class ImportResult(BaseModel):
    """Final result of completed import."""

    created: int
    skipped: int
    errors: int
    error_details: list[ImportRowError] = []


class ImportJobStatus(BaseModel):
    """Status of an import job."""

    job_id: UUID
    provider_id: UUID
    status: str  # pending, processing, completed, failed, cancelled
    progress: int  # 0-100
    total_rows: int
    processed_rows: int
    created: int
    skipped: int
    errors: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_file_url: str | None = None
    result: ImportResult | None = None


class ImportJobListItem(BaseModel):
    """List item for import job history."""

    id: UUID
    filename: str
    status: str
    total_rows: int
    created_count: int
    error_count: int
    created_at: datetime
    completed_at: datetime | None = None
    created_by_name: str | None = None


class ImportJobListResponse(BaseModel):
    """Response for import job history list."""

    items: list[ImportJobListItem]
    total: int
