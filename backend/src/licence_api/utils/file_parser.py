"""CSV file parser with auto-detection for license imports."""

import csv
import re
from typing import Any

import chardet

# Known column aliases for auto-mapping
COLUMN_ALIASES: dict[str, list[str]] = {
    "license_key": [
        "license_key",
        "license",
        "lizenz",
        "key",
        "schlüssel",
        "id",
        "license_id",
        "lizenz_id",
        "licensekey",
        "lizenzschlüssel",
    ],
    "external_user_id": [
        "external_user_id",
        "user_id",
        "benutzer_id",
        "user",
        "benutzer",
        "username",
        "benutzername",
        "account",
        "konto",
        "login",
    ],
    "license_type": [
        "license_type",
        "type",
        "typ",
        "art",
        "edition",
        "version",
        "lizenztyp",
        "plan",
        "tier",
        "stufe",
        "package",
        "paket",
    ],
    "employee_email": [
        "employee_email",
        "email",
        "e-mail",
        "mail",
        "benutzer_email",
        "user_email",
        "emailaddress",
        "e_mail",
        "mitarbeiter_email",
    ],
    "monthly_cost": [
        "monthly_cost",
        "cost",
        "kosten",
        "preis",
        "price",
        "betrag",
        "monatlich",
        "monthly",
        "monatliche_kosten",
        "amount",
        "gebühr",
    ],
    "currency": [
        "currency",
        "währung",
        "waehrung",
        "curr",
        "ccy",
    ],
    "valid_until": [
        "valid_until",
        "valid",
        "gültig_bis",
        "gueltig_bis",
        "ablauf",
        "expiry",
        "expires",
        "expires_at",
        "expiration",
        "ablaufdatum",
    ],
    "status": [
        "status",
        "zustand",
        "state",
        "aktiv",
        "active",
    ],
    "notes": [
        "notes",
        "notizen",
        "bemerkung",
        "comment",
        "kommentar",
        "description",
        "beschreibung",
        "anmerkung",
        "hinweis",
    ],
    "is_service_account": [
        "is_service_account",
        "service_account",
        "servicekonto",
        "service",
        "technical",
        "technisch",
        "bot",
    ],
    "service_account_name": [
        "service_account_name",
        "service_name",
        "servicename",
        "technical_name",
        "bot_name",
    ],
    "is_admin_account": [
        "is_admin_account",
        "admin_account",
        "admin",
        "administrator",
    ],
    "admin_account_name": [
        "admin_account_name",
        "admin_name",
        "adminname",
    ],
}


def detect_encoding(file_content: bytes) -> str:
    """Detect file encoding using chardet.

    Args:
        file_content: Raw file bytes

    Returns:
        Detected encoding (defaults to utf-8)
    """
    result = chardet.detect(file_content[:10000])  # Check first 10KB
    encoding = result.get("encoding", "utf-8")
    confidence = result.get("confidence", 0)

    # Default to utf-8 if confidence is low
    if encoding is None or confidence < 0.5:
        return "utf-8"

    # Normalize encoding names
    encoding_lower = encoding.lower()
    if encoding_lower in ("ascii", "iso-8859-1", "latin-1", "latin1"):
        return "utf-8"  # These are usually safe to treat as utf-8
    if encoding_lower in ("windows-1252", "cp1252"):
        return "cp1252"

    return encoding or "utf-8"


def detect_delimiter(sample: str) -> str:
    """Detect CSV delimiter from sample content.

    Args:
        sample: First few lines of the file as string

    Returns:
        Detected delimiter character
    """
    # Try common delimiters
    delimiters = [",", ";", "\t", "|"]
    counts: dict[str, int] = {}

    for delim in delimiters:
        # Count occurrences in first line
        first_line = sample.split("\n")[0]
        counts[delim] = first_line.count(delim)

    # Return delimiter with highest count (minimum 1)
    best = max(counts.items(), key=lambda x: x[1])
    return best[0] if best[1] > 0 else ","


def normalize_column_name(name: str) -> str:
    """Normalize column name for matching.

    Args:
        name: Original column name

    Returns:
        Normalized lowercase name without special chars
    """
    # Convert to lowercase
    normalized = name.lower().strip()
    # Replace common separators with underscore
    normalized = re.sub(r"[\s\-\.]+", "_", normalized)
    # Remove special characters except underscore
    normalized = re.sub(r"[^a-z0-9_äöüß]", "", normalized)
    return normalized


def suggest_column_mapping(columns: list[str]) -> dict[str, str | None]:
    """Suggest system field mappings for file columns.

    Args:
        columns: List of column names from file

    Returns:
        Dict mapping file column -> system field (or None)
    """
    mapping: dict[str, str | None] = {}
    used_fields: set[str] = set()

    for column in columns:
        normalized = normalize_column_name(column)
        matched_field: str | None = None

        # Check each system field's aliases
        for system_field, aliases in COLUMN_ALIASES.items():
            if system_field in used_fields:
                continue

            for alias in aliases:
                alias_normalized = normalize_column_name(alias)
                if normalized == alias_normalized or alias_normalized in normalized:
                    matched_field = system_field
                    used_fields.add(system_field)
                    break

            if matched_field:
                break

        mapping[column] = matched_field

    return mapping


def parse_csv_file(
    file_content: bytes,
    delimiter: str | None = None,
    encoding: str | None = None,
    has_header: bool = True,
    skip_rows: int = 0,
    max_rows: int = 1000,
) -> dict[str, Any]:
    """Parse a CSV file and return structured data.

    Args:
        file_content: Raw file bytes
        delimiter: CSV delimiter (auto-detect if None)
        encoding: File encoding (auto-detect if None)
        has_header: Whether first row is header
        skip_rows: Number of rows to skip at beginning
        max_rows: Maximum rows to read (for validation)

    Returns:
        Dict with columns, rows, and metadata

    Raises:
        ValueError: If file cannot be parsed
    """
    # Detect encoding if not provided
    if encoding is None:
        encoding = detect_encoding(file_content)

    # Decode content
    try:
        content = file_content.decode(encoding)
    except UnicodeDecodeError:
        # Fallback to utf-8 with error replacement
        content = file_content.decode("utf-8", errors="replace")

    # Remove BOM if present
    if content.startswith("\ufeff"):
        content = content[1:]

    # Detect delimiter if not provided
    if delimiter is None:
        delimiter = detect_delimiter(content)

    # Parse CSV
    lines = content.splitlines()

    # Skip initial rows if requested
    if skip_rows > 0:
        lines = lines[skip_rows:]

    if not lines:
        raise ValueError("File is empty or contains only skipped rows")

    reader = csv.reader(lines, delimiter=delimiter)
    rows_raw = list(reader)

    if not rows_raw:
        raise ValueError("No data found in file")

    # Extract columns
    if has_header:
        columns = [col.strip() for col in rows_raw[0]]
        data_rows = rows_raw[1:]
    else:
        # Generate column names (Column1, Column2, etc.)
        first_row = rows_raw[0]
        columns = [f"Column{i + 1}" for i in range(len(first_row))]
        data_rows = rows_raw

    # Validate columns
    if not columns:
        raise ValueError("No columns found in file")

    # Count total rows
    total_rows = len(data_rows)

    # Limit rows for preview/validation
    if len(data_rows) > max_rows:
        data_rows = data_rows[:max_rows]

    # Convert to list of dicts
    rows: list[dict[str, str]] = []
    for row in data_rows:
        if not any(cell.strip() for cell in row):
            continue  # Skip empty rows

        row_dict = {}
        for i, value in enumerate(row):
            if i < len(columns):
                row_dict[columns[i]] = value.strip()
        rows.append(row_dict)

    return {
        "columns": columns,
        "rows": rows,
        "total_rows": total_rows,
        "parsed_rows": len(rows),
        "encoding": encoding,
        "delimiter": delimiter,
        "has_header": has_header,
    }


def parse_boolean(value: str) -> bool | None:
    """Parse a boolean value from string.

    Args:
        value: String value to parse

    Returns:
        Boolean value or None if not parseable
    """
    if not value:
        return None

    value_lower = value.lower().strip()

    if value_lower in ("true", "yes", "ja", "1", "x", "y"):
        return True
    if value_lower in ("false", "no", "nein", "0", "", "n"):
        return False

    return None


def parse_date(value: str) -> str | None:
    """Parse and normalize a date string to ISO format.

    Args:
        value: Date string in various formats

    Returns:
        ISO date string (YYYY-MM-DD) or None
    """
    if not value or not value.strip():
        return None

    value = value.strip()

    # Common date patterns
    patterns = [
        # ISO format
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", "{0}-{1:02d}-{2:02d}"),
        # German format DD.MM.YYYY
        (r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", "{2}-{1:02d}-{0:02d}"),
        # US format MM/DD/YYYY
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "{2}-{0:02d}-{1:02d}"),
        # European format DD/MM/YYYY
        (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "{2}-{1:02d}-{0:02d}"),
    ]

    for pattern, fmt in patterns:
        match = re.match(pattern, value)
        if match:
            groups = [int(g) for g in match.groups()]
            try:
                return fmt.format(*groups)
            except (ValueError, IndexError):
                continue

    return None


def validate_email(value: str) -> bool:
    """Validate email format.

    Args:
        value: Email string

    Returns:
        True if valid email format
    """
    if not value:
        return False

    # Simple email regex
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, value.strip()))
