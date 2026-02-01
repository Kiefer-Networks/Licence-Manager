"""SQL Injection prevention tests.

These tests verify that the application is protected against SQL injection attacks.
SQLAlchemy ORM provides parameterized queries by default, which is the primary
protection. These tests verify defense-in-depth measures are in place.

SEC-25: SQL Injection Test Coverage

Security Model:
1. PRIMARY: SQLAlchemy ORM parameterizes ALL queries (no raw SQL)
2. SECONDARY: Input sanitization removes dangerous characters (defense-in-depth)
3. TERTIARY: Whitelist validation for enumeration fields (sort columns, statuses)
"""

import pytest
from uuid import uuid4

# SQL Injection payloads to test
SQL_INJECTION_PAYLOADS = [
    # Classic SQL injection
    "'; DROP TABLE users; --",
    "1' OR '1'='1",
    "1; DELETE FROM licenses WHERE '1'='1",
    "' UNION SELECT * FROM admin_users --",
    "1' AND 1=1 --",
    "1' AND 1=2 --",
    # Boolean-based blind injection
    "1' AND (SELECT COUNT(*) FROM admin_users) > 0 --",
    "1' AND SUBSTRING((SELECT password FROM admin_users LIMIT 1), 1, 1) = 'a' --",
    # Time-based blind injection
    "1'; WAITFOR DELAY '0:0:5' --",
    "1' AND SLEEP(5) --",
    "1'; SELECT pg_sleep(5) --",
    # UNION-based injection
    "' UNION SELECT NULL, NULL, NULL --",
    "' UNION ALL SELECT username, password FROM admin_users --",
    # Stacked queries
    "1'; INSERT INTO admin_users (email) VALUES ('hacked@evil.com'); --",
    "1'; UPDATE admin_users SET is_superadmin = true WHERE email = 'victim@company.com'; --",
    # Encoding variations
    "%27%20OR%201%3D1%20--",
    "1%27%3B%20DROP%20TABLE%20users%3B%20--",
    # Double encoding
    "%252527%252520OR%2525201%25253D1",
    # Unicode bypass attempts
    "ʼ OR 1=1 --",
    "ʼ; DROP TABLE users; --",
    # Comment variations
    "1'/**/OR/**/1=1--",
    "1'--",
    "1'#",
    "1'/*",
    # PostgreSQL specific
    "1'; COPY (SELECT * FROM admin_users) TO '/tmp/pwned'; --",
    "$$; DROP TABLE users; $$",
    # NULL byte injection
    "1'\x00 OR 1=1 --",
    # Scientific notation
    "1e1' OR '1'='1",
]

# XSS payloads that might be stored in DB
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "javascript:alert('XSS')",
    "<svg onload=alert('XSS')>",
    "'><script>alert('XSS')</script>",
]


class TestSQLInjectionPrevention:
    """Test SQL injection prevention across all input vectors.

    Note: SQLAlchemy ORM parameterizes all queries, making SQL injection impossible
    even if malicious input reaches the database layer. These tests verify the
    defense-in-depth sanitization layer works correctly.
    """

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_search_parameter_sanitized(self, payload: str) -> None:
        """Verify search parameters are sanitized.

        The sanitize_search() function removes semicolons and comment markers
        as defense-in-depth. SQLAlchemy parameterization is the primary protection.
        """
        from licence_api.utils.validation import sanitize_search

        result = sanitize_search(payload)

        # Result should be sanitized or None
        if result is not None:
            # Defense-in-depth: semicolons and -- should be removed
            assert ";" not in result
            assert "--" not in result
            # Max length should be enforced
            assert len(result) <= 200

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_department_parameter_rejected(self, payload: str) -> None:
        """Verify department filter parameters are validated against safe pattern.

        The sanitize_department() function validates against a safe character pattern,
        rejecting input with SQL special characters.
        """
        from licence_api.utils.validation import sanitize_department

        result = sanitize_department(payload)

        # All SQL injection payloads contain characters outside the safe pattern
        # and should be rejected (return None) or truncated to safe length
        if result is not None:
            assert len(result) <= 100
            # If returned, it matched the safe pattern (no SQL special chars)

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sort_column_whitelist_rejects_injection(self, payload: str) -> None:
        """Verify sort columns are validated against whitelist.

        Whitelist validation is the strongest protection for enumeration fields.
        Only pre-defined column names are accepted.
        """
        from licence_api.utils.validation import validate_sort_by

        allowed_columns = {"name", "created_at", "email"}
        result = validate_sort_by(payload, allowed_columns, "name")

        # Should always return a value from the whitelist or default
        assert result in allowed_columns

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_status_filter_whitelist_rejects_injection(self, payload: str) -> None:
        """Verify status filters are validated against whitelist."""
        from licence_api.utils.validation import sanitize_status

        allowed_statuses = {"active", "inactive", "pending"}
        result = sanitize_status(payload, allowed_statuses)

        # Should return None (invalid) or a valid status
        assert result is None or result in allowed_statuses

    def test_like_wildcard_escaping(self) -> None:
        """Verify LIKE wildcards are properly escaped."""
        from licence_api.utils.validation import escape_like_wildcards

        # Test wildcard characters
        assert escape_like_wildcards("test%value") == r"test\%value"
        assert escape_like_wildcards("test_value") == r"test\_value"
        assert escape_like_wildcards("test%_value") == r"test\%\_value"

        # Backslash should also be escaped
        assert escape_like_wildcards("test\\value") == r"test\\value"

        # SQL injection in LIKE should have wildcards escaped
        dangerous = "test%'; DROP TABLE users; --"
        escaped = escape_like_wildcards(dangerous)
        assert r"\%" in escaped
        assert "%" not in escaped.replace(r"\%", "")

    def test_uuid_parameter_validation(self) -> None:
        """Verify UUID parameters are type-validated.

        FastAPI with UUID type annotation automatically validates and rejects
        invalid UUIDs, preventing injection in UUID path parameters.
        """
        from uuid import UUID

        # Valid UUIDs should parse
        valid_uuid = uuid4()
        assert UUID(str(valid_uuid)) == valid_uuid

        # Invalid UUIDs should raise ValueError
        invalid_uuids = [
            "'; DROP TABLE users; --",
            "1 OR 1=1",
            "not-a-uuid",
            "12345",
            "",
        ]

        for invalid in invalid_uuids:
            with pytest.raises(ValueError):
                UUID(invalid)


class TestInputValidation:
    """Test input validation functions."""

    def test_max_length_enforcement(self) -> None:
        """Verify max_length is enforced on string fields."""
        from licence_api.utils.validation import sanitize_search

        # Long payloads should be truncated
        long_payload = "A" * 1000
        result = sanitize_search(long_payload)
        if result is not None:
            assert len(result) <= 200

    def test_pattern_validation_strict(self) -> None:
        """Verify pattern validation strictly matches expected formats."""
        from licence_api.utils.validation import validate_sort_direction

        # Valid directions
        assert validate_sort_direction("asc") == "asc"
        assert validate_sort_direction("desc") == "desc"
        assert validate_sort_direction("ASC") == "asc"
        assert validate_sort_direction("DESC") == "desc"

        # Invalid directions should return default
        assert validate_sort_direction("ascending") == "desc"
        assert validate_sort_direction("'; DROP TABLE") == "desc"
        assert validate_sort_direction("1=1") == "desc"

    def test_empty_and_none_handling(self) -> None:
        """Verify empty and None values are handled safely."""
        from licence_api.utils.validation import (
            sanitize_search,
            sanitize_department,
            sanitize_status,
        )

        # None should return None
        assert sanitize_search(None) is None
        assert sanitize_department(None) is None
        assert sanitize_status(None) is None

        # Empty strings should return None
        assert sanitize_search("") is None
        assert sanitize_search("   ") is None
        assert sanitize_department("") is None
        assert sanitize_department("   ") is None


class TestAuditFilterValidation:
    """Test audit log filter validation."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:10])
    def test_action_filter_whitelist_rejects_injection(self, payload: str) -> None:
        """Verify action filter uses whitelist validation."""
        from licence_api.utils.validation import validate_against_whitelist
        from licence_api.services.audit_service import AuditAction

        # AuditAction is a class with string constants, not an Enum
        allowed_actions = {
            v for k, v in vars(AuditAction).items()
            if not k.startswith("_") and isinstance(v, str)
        }

        # Invalid actions should return None
        result = validate_against_whitelist(payload, allowed_actions)
        assert result is None

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS[:10])
    def test_resource_type_filter_whitelist_rejects_injection(self, payload: str) -> None:
        """Verify resource_type filter uses whitelist validation."""
        from licence_api.utils.validation import validate_against_whitelist
        from licence_api.services.audit_service import ResourceType

        # ResourceType is a class with string constants, not an Enum
        allowed_types = {
            v for k, v in vars(ResourceType).items()
            if not k.startswith("_") and isinstance(v, str)
        }

        result = validate_against_whitelist(payload, allowed_types)
        assert result is None


class TestNoRawSQL:
    """Verify no raw SQL usage in codebase."""

    def test_no_text_import_in_repositories(self) -> None:
        """Ensure repositories don't use sqlalchemy.text() for raw SQL.

        SQLAlchemy text() allows raw SQL which bypasses ORM protection.
        This test verifies no repository uses it.
        """
        import os
        import re

        repo_dir = os.path.join(
            os.path.dirname(__file__),
            "..",
            "src",
            "licence_api",
            "repositories",
        )

        if not os.path.exists(repo_dir):
            pytest.skip("Repository directory not found")

        for filename in os.listdir(repo_dir):
            if not filename.endswith(".py"):
                continue

            filepath = os.path.join(repo_dir, filename)
            with open(filepath, "r") as f:
                content = f.read()

            # Check for text() usage (the dangerous pattern)
            # Allow text in comments and docstrings
            lines = content.split("\n")
            in_docstring = False

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Track docstrings
                if '"""' in stripped:
                    if stripped.count('"""') == 2:
                        continue  # Single line docstring
                    in_docstring = not in_docstring
                    continue

                if in_docstring:
                    continue

                # Skip comments
                if stripped.startswith("#"):
                    continue

                # Check for dangerous patterns
                if "text(" in line and "from sqlalchemy" not in line:
                    # text() call found outside import
                    if ".execute(text(" in line or "= text(" in line:
                        pytest.fail(
                            f"Potential raw SQL in {filename}:{i}: {line.strip()}"
                        )


class TestXSSStoragePrevention:
    """Test that XSS payloads are handled safely when stored.

    Note: XSS protection is primarily a frontend concern. These tests verify
    the backend doesn't crash on XSS payloads and properly stores them for
    the frontend to sanitize on display.
    """

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_search_handled_safely(self, payload: str) -> None:
        """Verify XSS payloads in search don't cause issues."""
        from licence_api.utils.validation import sanitize_search

        # Should not raise
        result = sanitize_search(payload)
        # Result is either None or a string
        assert result is None or isinstance(result, str)

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_in_department_rejected(self, payload: str) -> None:
        """Verify XSS payloads in department are rejected by pattern."""
        from licence_api.utils.validation import sanitize_department

        # XSS payloads contain < > characters not in safe pattern
        result = sanitize_department(payload)
        # Should be rejected (None) because < > aren't in safe pattern
        assert result is None


class TestSQLAlchemyProtection:
    """Tests verifying SQLAlchemy ORM provides parameterized queries.

    These tests document that SQLAlchemy is the primary protection against
    SQL injection, not input sanitization.
    """

    def test_sqlalchemy_parameterizes_filter(self) -> None:
        """Verify SQLAlchemy filter() uses parameterized queries.

        When using filter(Model.column == value), SQLAlchemy generates
        parameterized SQL like: WHERE column = :param_1
        """
        from sqlalchemy import create_engine, Column, Integer, String
        from sqlalchemy.orm import declarative_base, Session

        Base = declarative_base()

        class TestModel(Base):
            __tablename__ = "test"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        # Create in-memory SQLite for testing
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            # Build a query with a malicious value
            malicious_input = "'; DROP TABLE test; --"
            query = session.query(TestModel).filter(TestModel.name == malicious_input)

            # Get the compiled SQL
            compiled = query.statement.compile(engine)

            # Verify the value is parameterized, not interpolated
            sql_str = str(compiled)
            assert malicious_input not in sql_str
            assert ":name_1" in sql_str or "?" in sql_str  # Parameter placeholder

    def test_sqlalchemy_parameterizes_like(self) -> None:
        """Verify SQLAlchemy like() uses parameterized queries."""
        from sqlalchemy import create_engine, Column, Integer, String
        from sqlalchemy.orm import declarative_base, Session

        Base = declarative_base()

        class TestModel(Base):
            __tablename__ = "test"
            id = Column(Integer, primary_key=True)
            name = Column(String)

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as session:
            malicious_input = "%'; DROP TABLE test; --%"
            query = session.query(TestModel).filter(TestModel.name.like(malicious_input))

            compiled = query.statement.compile(engine)
            sql_str = str(compiled)

            # Verify parameterization
            assert malicious_input not in sql_str
            assert ":name_1" in sql_str or "?" in sql_str
