"""License-to-employee matching service with multi-level matching logic.

GDPR Note: This service does NOT store private email addresses.
It only creates temporary suggestions for manual review.
Admins decide what to do with each suggestion.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Literal
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from licence_api.models.domain.admin_user import AdminUser
from licence_api.models.orm.employee import EmployeeORM
from licence_api.models.orm.license import LicenseORM
from licence_api.repositories.employee_repository import EmployeeRepository
from licence_api.repositories.license_repository import LicenseRepository
from licence_api.services.audit_service import AuditAction, AuditService, ResourceType
from licence_api.services.cache_service import get_cache_service


# Match status constants
MATCH_STATUS_AUTO_MATCHED = "auto_matched"  # High confidence, auto-assigned
MATCH_STATUS_SUGGESTED = "suggested"  # Needs review
MATCH_STATUS_CONFIRMED = "confirmed"  # User confirmed suggestion
MATCH_STATUS_REJECTED = "rejected"  # User rejected suggestion
MATCH_STATUS_EXTERNAL_GUEST = "external_guest"  # Confirmed external guest
MATCH_STATUS_EXTERNAL_REVIEW = "external_review"  # External email, needs review

# Match method constants
MATCH_METHOD_EXACT = "exact_email"
MATCH_METHOD_LOCAL_PART = "local_part"
MATCH_METHOD_FUZZY_NAME = "fuzzy_name"

# Confidence thresholds
CONFIDENCE_AUTO_ASSIGN = 0.95  # Auto-assign if confidence >= this
CONFIDENCE_SUGGEST = 0.5  # Suggest if confidence >= this

MatchStatus = Literal[
    "auto_matched", "suggested", "confirmed", "rejected",
    "external_guest", "external_review"
]
MatchMethod = Literal["exact_email", "local_part", "fuzzy_name"]


@dataclass
class MatchResult:
    """Result of a license-to-employee match attempt."""

    employee_id: UUID | None = None
    confidence: float = 0.0
    method: MatchMethod | None = None
    status: MatchStatus | None = None
    is_external: bool = False

    @property
    def should_auto_assign(self) -> bool:
        """Check if match should be auto-assigned."""
        return (
            self.employee_id is not None
            and self.confidence >= CONFIDENCE_AUTO_ASSIGN
        )

    @property
    def should_suggest(self) -> bool:
        """Check if match should be suggested for review."""
        return (
            self.employee_id is not None
            and CONFIDENCE_SUGGEST <= self.confidence < CONFIDENCE_AUTO_ASSIGN
        )


class MatchingService:
    """Service for matching licenses to employees.

    GDPR-compliant: Does not store private email addresses.
    Only creates suggestions for manual review.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.employee_repo = EmployeeRepository(session)
        self.license_repo = LicenseRepository(session)
        self.audit_service = AuditService(session)

        # Caches populated during matching
        self._email_to_employee: dict[str, EmployeeORM] = {}
        self._local_to_employees: dict[str, list[EmployeeORM]] = {}
        self._employees_by_id: dict[UUID, EmployeeORM] = {}

    async def _build_caches(self) -> None:
        """Build lookup caches for efficient matching."""
        # Get all employees
        employees = await self.employee_repo.get_all()

        for emp in employees:
            # Store by ID
            self._employees_by_id[emp.id] = emp

            # Email lookup (lowercase)
            email_lower = emp.email.lower()
            self._email_to_employee[email_lower] = emp

            # Local part lookup (before @)
            if "@" in email_lower:
                local = email_lower.split("@")[0]
                if local not in self._local_to_employees:
                    self._local_to_employees[local] = []
                self._local_to_employees[local].append(emp)

    def _is_external_email(
        self,
        email: str,
        company_domains: list[str],
    ) -> bool:
        """Check if an email is external (not from company domains).

        Args:
            email: Email address to check
            company_domains: List of company domain names

        Returns:
            True if email is external
        """
        if not email or "@" not in email:
            return True  # Treat non-email identifiers as external

        domain = email.split("@")[1].lower()

        for company_domain in company_domains:
            cd = company_domain.lower()
            # Exact match or subdomain match
            if domain == cd or domain.endswith("." + cd):
                return False

        return True

    def _extract_name_from_email(self, email: str) -> str | None:
        """Extract a potential name from an email local part.

        Handles formats like:
        - john.doe@domain.com -> "john doe"
        - john_doe@domain.com -> "john doe"
        - johndoe@domain.com -> "johndoe"
        """
        if "@" not in email:
            return None

        local = email.split("@")[0].lower()
        # Replace common separators with space
        name = re.sub(r"[._\-]", " ", local)
        # Remove numbers
        name = re.sub(r"\d+", "", name)
        return name.strip() if name.strip() else None

    def _fuzzy_name_match(
        self,
        license_email: str,
        employees: list[EmployeeORM],
    ) -> tuple[EmployeeORM | None, float]:
        """Find best fuzzy name match from email to employee names.

        Args:
            license_email: License email address
            employees: List of employees to match against

        Returns:
            Tuple of (best_match_employee, confidence)
        """
        email_name = self._extract_name_from_email(license_email)
        if not email_name:
            return None, 0.0

        best_match: EmployeeORM | None = None
        best_score = 0.0

        for emp in employees:
            emp_name = emp.full_name.lower()

            # Direct name comparison
            score = SequenceMatcher(None, email_name, emp_name).ratio()

            # Also try reversed name parts (for "doe john" vs "john doe")
            email_parts = email_name.split()
            if len(email_parts) == 2:
                reversed_email = f"{email_parts[1]} {email_parts[0]}"
                reversed_score = SequenceMatcher(
                    None, reversed_email, emp_name
                ).ratio()
                score = max(score, reversed_score)

            # Check if first.last or last.first pattern matches
            name_parts = emp_name.split()
            if len(name_parts) >= 2:
                first_last = f"{name_parts[0]} {name_parts[-1]}"
                last_first = f"{name_parts[-1]} {name_parts[0]}"
                score = max(
                    score,
                    SequenceMatcher(None, email_name, first_last).ratio(),
                    SequenceMatcher(None, email_name, last_first).ratio(),
                )

            if score > best_score:
                best_score = score
                best_match = emp

        # Apply confidence adjustment for fuzzy matching
        # Fuzzy matches are inherently less reliable
        confidence = best_score * 0.85  # Max 85% confidence for fuzzy

        return best_match, confidence

    async def match_license(
        self,
        external_user_id: str,
        company_domains: list[str],
    ) -> MatchResult:
        """Match a license to an employee using multi-level matching.

        Matching levels (in order of priority):
        1. Exact email match (company email)
        2. Local part match (e.g., john.doe@ matches john.doe@company.com)
        3. Fuzzy name match (e.g., "john.doe" matches employee "John Doe")

        Args:
            external_user_id: The license's external user ID (usually email)
            company_domains: List of company email domains

        Returns:
            MatchResult with match details
        """
        email = external_user_id.lower().strip()
        is_external = self._is_external_email(email, company_domains)

        # Build caches if not done
        if not self._email_to_employee:
            await self._build_caches()

        # Level 1: Exact email match (only for company emails)
        if email in self._email_to_employee:
            emp = self._email_to_employee[email]
            return MatchResult(
                employee_id=emp.id,
                confidence=1.0,
                method=MATCH_METHOD_EXACT,
                status=MATCH_STATUS_AUTO_MATCHED,
                is_external=False,
            )

        # For remaining levels, only process if email format
        if "@" not in email:
            return MatchResult(
                is_external=True,
                status=MATCH_STATUS_EXTERNAL_REVIEW,
            )

        local = email.split("@")[0]

        # Level 2: Local part match
        if local in self._local_to_employees:
            candidates = self._local_to_employees[local]
            if len(candidates) == 1:
                # Unique match by local part
                emp = candidates[0]
                # For external emails, always suggest (needs review for GDPR)
                return MatchResult(
                    employee_id=emp.id,
                    confidence=0.85 if is_external else 0.90,
                    method=MATCH_METHOD_LOCAL_PART,
                    status=MATCH_STATUS_SUGGESTED,
                    is_external=is_external,
                )
            elif len(candidates) > 1:
                # Multiple matches - try fuzzy name matching
                best_emp, confidence = self._fuzzy_name_match(
                    email, candidates
                )
                if best_emp and confidence >= CONFIDENCE_SUGGEST:
                    return MatchResult(
                        employee_id=best_emp.id,
                        confidence=confidence,
                        method=MATCH_METHOD_FUZZY_NAME,
                        status=MATCH_STATUS_SUGGESTED,
                        is_external=is_external,
                    )

        # Level 3: Fuzzy name match against all employees (only for external)
        if is_external:
            all_employees = list(self._employees_by_id.values())
            best_emp, confidence = self._fuzzy_name_match(email, all_employees)

            if best_emp and confidence >= CONFIDENCE_SUGGEST:
                return MatchResult(
                    employee_id=best_emp.id,
                    confidence=confidence,
                    method=MATCH_METHOD_FUZZY_NAME,
                    status=MATCH_STATUS_SUGGESTED,
                    is_external=is_external,
                )

        # No match found
        if is_external:
            return MatchResult(
                is_external=True,
                status=MATCH_STATUS_EXTERNAL_REVIEW,
            )
        else:
            # Internal email but no match - "unknown internal"
            return MatchResult(
                is_external=False,
                status=None,  # Will be handled as "not_in_hris"
            )

    async def process_license_matches(
        self,
        licenses: list[LicenseORM],
        company_domains: list[str],
    ) -> dict[str, int]:
        """Process matches for multiple licenses.

        Args:
            licenses: List of licenses to process
            company_domains: Company email domains

        Returns:
            Dict with counts: auto_matched, suggested, external, unmatched
        """
        stats = {
            "auto_matched": 0,
            "suggested": 0,
            "external": 0,
            "unmatched": 0,
        }

        await self._build_caches()

        for license in licenses:
            result = await self.match_license(
                license.external_user_id,
                company_domains,
            )

            if result.should_auto_assign:
                # Auto-assign the employee
                license.employee_id = result.employee_id
                license.match_confidence = result.confidence
                license.match_method = result.method
                license.match_status = result.status
                stats["auto_matched"] += 1

            elif result.should_suggest:
                # Create a suggestion (no private email stored!)
                license.suggested_employee_id = result.employee_id
                license.match_confidence = result.confidence
                license.match_method = result.method
                license.match_status = result.status
                stats["suggested"] += 1

            elif result.is_external:
                license.match_status = MATCH_STATUS_EXTERNAL_REVIEW
                stats["external"] += 1

            else:
                stats["unmatched"] += 1

        await self.session.flush()
        return stats

    async def confirm_match(
        self,
        license_id: UUID,
        admin_user_id: UUID,
    ) -> LicenseORM | None:
        """Confirm a suggested match.

        Args:
            license_id: License UUID
            admin_user_id: Admin user who confirmed

        Returns:
            Updated license or None if not found
        """
        license = await self.license_repo.get(license_id)
        if not license or not license.suggested_employee_id:
            return None

        # Move suggestion to actual assignment
        license.employee_id = license.suggested_employee_id
        license.suggested_employee_id = None
        license.match_status = MATCH_STATUS_CONFIRMED
        license.match_reviewed_at = datetime.now(timezone.utc)
        license.match_reviewed_by = admin_user_id

        await self.session.flush()
        await self.session.refresh(license)
        return license

    async def reject_match(
        self,
        license_id: UUID,
        admin_user_id: UUID,
    ) -> LicenseORM | None:
        """Reject a suggested match.

        Args:
            license_id: License UUID
            admin_user_id: Admin user who rejected

        Returns:
            Updated license or None if not found
        """
        license = await self.license_repo.get(license_id)
        if not license:
            return None

        license.suggested_employee_id = None
        license.match_status = MATCH_STATUS_REJECTED
        license.match_reviewed_at = datetime.now(timezone.utc)
        license.match_reviewed_by = admin_user_id

        await self.session.flush()
        await self.session.refresh(license)
        return license

    async def mark_as_external_guest(
        self,
        license_id: UUID,
        admin_user_id: UUID,
    ) -> LicenseORM | None:
        """Mark a license as belonging to an external guest.

        Args:
            license_id: License UUID
            admin_user_id: Admin user who marked

        Returns:
            Updated license or None if not found
        """
        license = await self.license_repo.get(license_id)
        if not license:
            return None

        license.employee_id = None
        license.suggested_employee_id = None
        license.match_status = MATCH_STATUS_EXTERNAL_GUEST
        license.match_reviewed_at = datetime.now(timezone.utc)
        license.match_reviewed_by = admin_user_id

        await self.session.flush()
        await self.session.refresh(license)
        return license

    async def assign_to_employee(
        self,
        license_id: UUID,
        employee_id: UUID,
        admin_user_id: UUID,
    ) -> LicenseORM | None:
        """Manually assign a license to an employee.

        Args:
            license_id: License UUID
            employee_id: Employee UUID to assign
            admin_user_id: Admin user who assigned

        Returns:
            Updated license or None if not found
        """
        license = await self.license_repo.get(license_id)
        if not license:
            return None

        license.employee_id = employee_id
        license.suggested_employee_id = None
        license.match_confidence = 1.0
        license.match_method = None  # Manual assignment
        license.match_status = MATCH_STATUS_CONFIRMED
        license.match_reviewed_at = datetime.now(timezone.utc)
        license.match_reviewed_by = admin_user_id

        await self.session.flush()
        await self.session.refresh(license)
        return license

    async def get_pending_suggestions(
        self,
        provider_id: UUID | None = None,
        limit: int = 100,
    ) -> list[tuple[LicenseORM, EmployeeORM | None]]:
        """Get licenses with pending match suggestions.

        Args:
            provider_id: Optional provider filter
            limit: Maximum results

        Returns:
            List of (license, suggested_employee) tuples
        """
        from sqlalchemy import select

        query = (
            select(LicenseORM, EmployeeORM)
            .outerjoin(
                EmployeeORM,
                LicenseORM.suggested_employee_id == EmployeeORM.id
            )
            .where(LicenseORM.match_status == MATCH_STATUS_SUGGESTED)
        )

        if provider_id:
            query = query.where(LicenseORM.provider_id == provider_id)

        query = query.order_by(
            LicenseORM.match_confidence.desc()
        ).limit(limit)

        result = await self.session.execute(query)
        return list(result.all())

    async def get_external_for_review(
        self,
        provider_id: UUID | None = None,
        limit: int = 100,
    ) -> list[LicenseORM]:
        """Get external licenses pending review.

        Args:
            provider_id: Optional provider filter
            limit: Maximum results

        Returns:
            List of licenses with external_review status
        """
        from sqlalchemy import select

        query = (
            select(LicenseORM)
            .where(LicenseORM.match_status == MATCH_STATUS_EXTERNAL_REVIEW)
        )

        if provider_id:
            query = query.where(LicenseORM.provider_id == provider_id)

        query = query.order_by(LicenseORM.external_user_id).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # Methods with commit (for use from routers)
    # =========================================================================

    async def confirm_match_with_commit(
        self,
        license_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> LicenseORM | None:
        """Confirm a suggested match with full side effects.

        Args:
            license_id: License UUID
            user: Admin user who confirmed
            request: HTTP request for audit logging

        Returns:
            Updated license or None if not found
        """
        license = await self.confirm_match(license_id, user.id)
        if license is None:
            return None

        # Audit log the confirmation
        await self.audit_service.log(
            action=AuditAction.LICENSE_ASSIGN,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=user.id,
            changes={
                "match_confirmed": True,
                "employee_id": str(license.employee_id),
            },
            request=request,
        )

        # Invalidate dashboard cache
        cache = await get_cache_service()
        await cache.invalidate_dashboard()

        await self.session.commit()
        return license

    async def reject_match_with_commit(
        self,
        license_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> LicenseORM | None:
        """Reject a suggested match with full side effects.

        Args:
            license_id: License UUID
            user: Admin user who rejected
            request: HTTP request for audit logging

        Returns:
            Updated license or None if not found
        """
        license = await self.reject_match(license_id, user.id)
        if license is None:
            return None

        # Audit log the rejection
        await self.audit_service.log(
            action=AuditAction.LICENSE_UPDATE,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=user.id,
            changes={"match_rejected": True},
            request=request,
        )

        await self.session.commit()
        return license

    async def mark_as_external_guest_with_commit(
        self,
        license_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> LicenseORM | None:
        """Mark a license as external guest with full side effects.

        Args:
            license_id: License UUID
            user: Admin user who marked
            request: HTTP request for audit logging

        Returns:
            Updated license or None if not found
        """
        license = await self.mark_as_external_guest(license_id, user.id)
        if license is None:
            return None

        # Audit log the change
        await self.audit_service.log(
            action=AuditAction.LICENSE_UPDATE,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=user.id,
            changes={"marked_as_external_guest": True},
            request=request,
        )

        # Invalidate dashboard cache
        cache = await get_cache_service()
        await cache.invalidate_dashboard()

        await self.session.commit()
        return license

    async def assign_to_employee_with_commit(
        self,
        license_id: UUID,
        employee_id: UUID,
        user: AdminUser,
        request: Request | None = None,
    ) -> LicenseORM | None:
        """Manually assign a license to an employee with full side effects.

        Args:
            license_id: License UUID
            employee_id: Employee UUID to assign
            user: Admin user who assigned
            request: HTTP request for audit logging

        Returns:
            Updated license or None if not found
        """
        license = await self.assign_to_employee(license_id, employee_id, user.id)
        if license is None:
            return None

        # Audit log the assignment
        await self.audit_service.log(
            action=AuditAction.LICENSE_ASSIGN,
            resource_type=ResourceType.LICENSE,
            resource_id=license_id,
            admin_user_id=user.id,
            changes={
                "employee_id": str(employee_id),
                "manual_assignment": True,
            },
            request=request,
        )

        # Invalidate dashboard cache
        cache = await get_cache_service()
        await cache.invalidate_dashboard()

        await self.session.commit()
        return license
