"""HiBob HRIS provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import HRISProvider

logger = logging.getLogger(__name__)


def parse_date(date_str: str | None):
    """Parse date string in various formats.

    HiBob returns dates in different formats:
    - YYYY-MM-DD (ISO format)
    - DD/MM/YYYY (human readable format)
    """
    if not date_str:
        return None

    # Try different formats
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None


class HiBobProvider(HRISProvider):
    """HiBob HRIS integration for employee data."""

    BASE_URL = "https://api.hibob.com/v1"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize HiBob provider.

        Args:
            credentials: Dict with keys:
                - auth_token: Base64 encoded string for Basic auth (user:password)
        """
        super().__init__(credentials)
        self.auth_token = credentials.get("auth_token", "")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Basic {self.auth_token}",
            "Accept": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test HiBob API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Use /people/search to test - same as fetch_employees
                response = await client.post(
                    f"{self.BASE_URL}/people/search",
                    headers=self._get_headers(),
                    json={"showInactive": False, "humanReadable": "REPLACE"},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_employees(self) -> list[dict[str, Any]]:
        """Fetch all employees from HiBob.

        Returns:
            List of employee data dicts
        """
        employees = []

        async with httpx.AsyncClient() as client:
            # First, get manager emails from /people/search WITHOUT humanReadable
            # This gives us reportsTo as a dict with email
            manager_response = await client.post(
                f"{self.BASE_URL}/people/search",
                headers=self._get_headers(),
                json={"showInactive": False},  # No humanReadable = raw values
                timeout=30.0,
            )
            manager_response.raise_for_status()
            manager_data = manager_response.json()

            # Build mapping of employee ID to manager email
            manager_email_map: dict[str, str] = {}
            for emp in manager_data.get("employees", []):
                work = emp.get("work", {})
                reports_to = work.get("reportsTo", {})
                if isinstance(reports_to, dict):
                    manager_email = reports_to.get("email", "").lower()
                    if manager_email:
                        manager_email_map[emp.get("id")] = manager_email

            # Now get employee data with humanReadable for readable department names
            response = await client.post(
                f"{self.BASE_URL}/people/search",
                headers=self._get_headers(),
                json={"showInactive": False, "humanReadable": "REPLACE"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for emp in data.get("employees", []):
                # Extract work info
                work = emp.get("work", {})

                # Parse dates using flexible parser
                termination_date = parse_date(work.get("terminationDate"))
                start_date = parse_date(work.get("startDate"))

                # Determine status
                status = "active"
                if termination_date and termination_date <= datetime.now().date():
                    status = "offboarded"

                # Build full name - use displayName if available, else firstName + surname
                full_name = emp.get("displayName", "")
                if not full_name:
                    first_name = emp.get("firstName", "")
                    surname = emp.get("surname", "")
                    full_name = f"{first_name} {surname}".strip()

                # Get manager email from the mapping we built earlier
                emp_id = emp.get("id")
                manager_email = manager_email_map.get(emp_id)

                employees.append({
                    "hibob_id": emp_id,
                    "email": emp.get("email", "").lower(),
                    "full_name": full_name,
                    "department": work.get("department"),
                    "status": status,
                    "start_date": start_date,
                    "termination_date": termination_date,
                    "manager_email": manager_email,
                    "avatar_url": f"/api/v1/users/employees/avatar/{emp_id}",
                })

        return employees

    async def fetch_avatar(self, hibob_id: str) -> bytes | None:
        """Fetch employee avatar from HiBob.

        HiBob's avatar endpoint returns a URL to the actual image,
        so we need to fetch that URL and then download the image.

        Args:
            hibob_id: HiBob employee ID

        Returns:
            Avatar image bytes or None if not found
        """
        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get the avatar URL from HiBob
                url = f"{self.BASE_URL}/avatars/{hibob_id}"
                response = await client.get(
                    url,
                    headers=self._get_headers(),
                    timeout=10.0,
                )

                if response.status_code == 429:
                    # Rate limited - raise exception so caller can retry
                    raise Exception(f"429 Rate Limited: {response.text[:100]}")

                if response.status_code != 200:
                    logger.warning("Avatar URL fetch failed for %s: status=%d", hibob_id, response.status_code)
                    return None

                # Parse the response - could be JSON with URL or just the URL string
                content_type = response.headers.get("content-type", "")

                # If response is already an image, return it directly
                if content_type.startswith("image/"):
                    logger.info(f"Avatar fetched directly for {hibob_id}, content-type: {content_type}, size: {len(response.content)} bytes")
                    return response.content

                # Otherwise, parse as JSON or text to get the URL
                try:
                    data = response.json()
                    avatar_url = data if isinstance(data, str) else data.get("url") or data.get("avatarUrl")
                except Exception:
                    # Try as plain text
                    avatar_url = response.text.strip().strip('"')

                if not avatar_url:
                    logger.warning("No avatar URL found in response for %s", hibob_id)
                    return None

                logger.info(f"Got avatar URL for {hibob_id}: {avatar_url}")

                # Step 2: Fetch the actual image from the URL
                img_response = await client.get(avatar_url, timeout=10.0, follow_redirects=True)
                if img_response.status_code == 200:
                    logger.info(f"Avatar image fetched for {hibob_id}, size: {len(img_response.content)} bytes")
                    return img_response.content

                logger.warning(f"Avatar image download failed for {hibob_id}: status={img_response.status_code}")
                return None

        except Exception as e:
            logger.exception(f"Avatar fetch error for {hibob_id}: {e}")
            return None
