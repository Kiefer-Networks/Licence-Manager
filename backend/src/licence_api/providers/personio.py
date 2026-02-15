"""Personio HRIS provider integration."""

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from licence_api.providers.base import HRISProvider

logger = logging.getLogger(__name__)


def parse_date(date_str: str | None):
    """Parse date string from Personio API.

    Personio typically returns dates in YYYY-MM-DD format.
    """
    if not date_str:
        return None

    # Try different formats
    for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


class PersonioProvider(HRISProvider):
    """Personio HRIS integration for employee data.

    Personio uses OAuth 2.0 with Client Credentials flow.
    API Documentation: https://developer.personio.de/docs
    """

    AUTH_URL = "https://api.personio.de/v1/auth"
    BASE_URL = "https://api.personio.de/v1"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Personio provider.

        Args:
            credentials: Dict with keys:
                - client_id: Personio API client ID
                - client_secret: Personio API client secret
        """
        super().__init__(credentials)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        """Get or refresh OAuth access token.

        Personio tokens are valid for 24 hours.

        Args:
            client: HTTP client instance

        Returns:
            Valid access token
        """
        # Check if we have a valid cached token
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(UTC) < self._token_expires_at
        ):
            return self._access_token

        # Request new token
        response = await client.post(
            self.AUTH_URL,
            json={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise ValueError(
                f"Personio auth failed: {data.get('error', {}).get('message', 'Unknown error')}"
            )

        token_data = data.get("data", {})
        self._access_token = token_data.get("token")

        # Token expires in 24 hours, but we'll refresh 1 hour early to be safe
        self._token_expires_at = datetime.now(UTC).replace(hour=23, minute=0, second=0)

        logger.info("Personio OAuth token acquired")
        return self._access_token

    def _get_headers(self, token: str) -> dict[str, str]:
        """Get API request headers with auth token."""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-Personio-Partner-ID": "LICENCE_MANAGEMENT",
            "X-Personio-App-ID": "licence-management",
        }

    async def test_connection(self) -> bool:
        """Test Personio API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                token = await self._get_access_token(client)
                # Test with a simple employees request (limit 1)
                response = await client.get(
                    f"{self.BASE_URL}/company/employees",
                    headers=self._get_headers(token),
                    params={"limit": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Personio connection test failed: {e}")
            return False

    async def fetch_employees(self) -> list[dict[str, Any]]:
        """Fetch all employees from Personio.

        Uses pagination to fetch all employees.
        API: GET /company/employees

        Returns:
            List of employee data dicts
        """
        employees = []
        offset = 0
        limit = 100  # Personio max is 100 (starting May 2025)

        async with httpx.AsyncClient() as client:
            token = await self._get_access_token(client)

            while True:
                response = await client.get(
                    f"{self.BASE_URL}/company/employees",
                    headers=self._get_headers(token),
                    params={
                        "limit": limit,
                        "offset": offset,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    raise ValueError(
                        f"Personio API error: {data.get('error', {}).get('message', 'Unknown')}"
                    )

                employee_list = data.get("data", [])
                if not employee_list:
                    break

                for emp in employee_list:
                    parsed = self._parse_employee(emp)
                    if parsed:
                        employees.append(parsed)

                # Check if we got less than limit (no more pages)
                if len(employee_list) < limit:
                    break

                offset += limit
                logger.info(f"Personio: fetched {len(employees)} employees so far...")

        logger.info(f"Personio: fetched {len(employees)} employees total")
        return employees

    def _parse_employee(self, emp: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Personio employee data into our format.

        Personio returns employee attributes in a nested structure:
        {
            "type": "Employee",
            "attributes": {
                "id": {"label": "ID", "value": 123},
                "email": {"label": "Email", "value": "john@company.com"},
                ...
            }
        }

        Args:
            emp: Raw employee data from Personio

        Returns:
            Parsed employee dict or None if invalid
        """
        attrs = emp.get("attributes", {})

        def get_attr(name: str, default: Any = None) -> Any:
            """Extract attribute value from Personio nested structure."""
            attr = attrs.get(name, {})
            if isinstance(attr, dict):
                return attr.get("value", default)
            return default

        # Required fields
        personio_id = get_attr("id")
        email = get_attr("email", "")

        if not personio_id or not email:
            logger.warning("Skipping Personio employee without ID or email")
            return None

        # Build full name
        first_name = get_attr("first_name", "")
        last_name = get_attr("last_name", "")
        full_name = f"{first_name} {last_name}".strip()

        if not full_name:
            full_name = email.split("@")[0]  # Fallback

        # Status mapping
        # Personio statuses: active, onboarding, leave, inactive
        raw_status = get_attr("status", "active")
        status = "active" if raw_status in ("active", "onboarding", "leave") else "offboarded"

        # Dates
        hire_date = parse_date(get_attr("hire_date"))
        termination_date = parse_date(get_attr("termination_date"))

        # Override status if termination date is in the past
        if termination_date and termination_date <= datetime.now().date():
            status = "offboarded"

        # Department - can be nested object with name
        department_attr = get_attr("department")
        department = None
        if isinstance(department_attr, dict):
            department = department_attr.get("attributes", {}).get("name", {}).get("value")
        elif isinstance(department_attr, str):
            department = department_attr

        # Manager/Supervisor - Personio uses 'supervisor' field
        supervisor_attr = get_attr("supervisor")
        manager_email = None
        if isinstance(supervisor_attr, dict):
            # Supervisor is usually a nested employee reference
            sup_attrs = supervisor_attr.get("attributes", {})
            if sup_attrs:
                sup_email = sup_attrs.get("email", {})
                if isinstance(sup_email, dict):
                    manager_email = sup_email.get("value", "").lower() or None
                elif isinstance(sup_email, str) and "@" in sup_email:
                    manager_email = sup_email.lower()

        return {
            "hibob_id": str(personio_id),  # Use hibob_id field for all HRIS providers
            "email": email.lower(),
            "full_name": full_name,
            "department": department,
            "status": status,
            "start_date": hire_date,
            "termination_date": termination_date,
            "manager_email": manager_email,
            "avatar_url": None,  # Personio doesn't provide avatars via API
        }

    async def fetch_avatar(self, employee_id: str) -> bytes | None:
        """Personio does not provide employee avatars via API.

        Returns:
            Always None
        """
        return None
