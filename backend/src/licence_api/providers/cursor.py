"""Cursor provider integration."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class CursorProvider(BaseProvider):
    """Cursor IDE integration for developer licenses.

    API: https://api.cursor.com
    Auth: Basic auth with API key
    Endpoints:
        - GET /teams/members - Team members with roles
        - POST /teams/spend - Billing cycle spending per user
        - POST /teams/daily-usage-data - Daily usage metrics
    """

    BASE_URL = "https://api.cursor.com"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Cursor provider.

        Args:
            credentials: Dict with keys:
                - api_key: Cursor API key
        """
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")

    def _get_auth(self) -> httpx.BasicAuth:
        """Get Basic auth for API requests."""
        # Cursor uses API key as username with empty password (like -u API_KEY:)
        return httpx.BasicAuth(self.api_key, "")

    async def test_connection(self) -> bool:
        """Test Cursor API connection.

        Returns:
            True if connection is successful

        Raises:
            ValueError: If credentials are invalid (401)
        """
        if not self.api_key:
            raise ValueError("API key is required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/teams/members",
                    auth=self._get_auth(),
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    raise ValueError("Invalid API key")
                elif response.status_code == 403:
                    raise ValueError("Access forbidden - check API key permissions")
                else:
                    raise ValueError(f"API error: {response.status_code}")
        except httpx.RequestError as e:
            raise ValueError(f"Connection error: {str(e)}")

    async def _fetch_spend_data(self, client: httpx.AsyncClient) -> dict[str, dict]:
        """Fetch current billing cycle spend per user.

        Returns:
            Dict mapping email to spend data
        """
        spend_by_email: dict[str, dict] = {}
        try:
            response = await client.post(
                f"{self.BASE_URL}/teams/spend",
                auth=self._get_auth(),
                json={},
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                for user in data.get("users", []):
                    email = user.get("email", "").lower()
                    if email:
                        # Spend is in cents
                        spend_cents = user.get("spend", 0)
                        spend_by_email[email] = {
                            "spend_cents": spend_cents,
                            "spend_usd": Decimal(spend_cents) / 100,
                        }
        except Exception:
            pass
        return spend_by_email

    async def _fetch_usage_data(self, client: httpx.AsyncClient) -> dict[str, datetime]:
        """Fetch last activity date per user from usage data.

        Returns:
            Dict mapping email to last activity datetime
        """
        last_activity: dict[str, datetime] = {}
        try:
            # Get last 30 days of usage
            end_date = datetime.now(UTC)
            start_date = end_date - timedelta(days=30)

            response = await client.post(
                f"{self.BASE_URL}/teams/daily-usage-data",
                auth=self._get_auth(),
                json={
                    "startDate": start_date.strftime("%Y-%m-%d"),
                    "endDate": end_date.strftime("%Y-%m-%d"),
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                for day_data in data.get("data", []):
                    date_str = day_data.get("date")
                    if not date_str:
                        continue
                    try:
                        activity_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    except ValueError:
                        continue

                    for user in day_data.get("users", []):
                        email = user.get("email", "").lower()
                        if email:
                            # Track most recent activity
                            if email not in last_activity or activity_date > last_activity[email]:
                                # Only count as activity if there was actual usage
                                total_requests = (
                                    user.get("composerRequests", 0)
                                    + user.get("chatRequests", 0)
                                    + user.get("agentRequests", 0)
                                    + user.get("tabsAccepted", 0)
                                )
                                if total_requests > 0:
                                    last_activity[email] = activity_date
        except Exception:
            pass
        return last_activity

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch team members from Cursor with spend and usage data.

        Returns:
            List of license data dicts
        """
        if not self.api_key:
            return []

        licenses = []

        try:
            async with httpx.AsyncClient() as client:
                # Fetch members
                response = await client.get(
                    f"{self.BASE_URL}/teams/members",
                    auth=self._get_auth(),
                    timeout=30.0,
                )
                response.raise_for_status()
                members_data = response.json()

                # Fetch spend and usage data
                spend_data = await self._fetch_spend_data(client)
                usage_data = await self._fetch_usage_data(client)

                for member in members_data.get("teamMembers", []):
                    email = member.get("email", "").lower()
                    role = member.get("role", "member")

                    # Determine license type based on role
                    if role == "unpaid admin":
                        license_type = "Admin (Unpaid)"
                        monthly_cost = Decimal("0.00")
                    elif role == "owner":
                        license_type = "Owner"
                        monthly_cost = Decimal("20.00")
                    else:
                        license_type = "Pro"
                        monthly_cost = Decimal("20.00")

                    # Get spend data for this user
                    user_spend = spend_data.get(email, {})
                    current_spend = user_spend.get("spend_usd", Decimal("0.00"))

                    # Get last activity
                    last_activity = usage_data.get(email)

                    licenses.append(
                        {
                            "external_user_id": email,
                            "email": email,
                            "license_type": license_type,
                            "status": "active",
                            "monthly_cost": monthly_cost,
                            "currency": "USD",
                            "last_activity_at": last_activity,
                            "metadata": {
                                "name": member.get("name"),
                                "role": role,
                                "current_spend_usd": str(current_spend),
                            },
                        }
                    )
        except Exception:
            pass

        return licenses

    def _parse_manual_data(self) -> list[dict[str, Any]]:
        """Parse manually provided user data.

        Expected format for manual_data:
        [
            {"email": "user@example.com", "name": "User Name", "plan": "Pro"},
            ...
        ]

        Returns:
            List of license data dicts
        """
        licenses = []

        for entry in self.manual_data:
            licenses.append(
                {
                    "external_user_id": entry.get("email", "").lower(),
                    "email": entry.get("email", "").lower(),
                    "license_type": entry.get("plan", "Pro"),
                    "status": "active",
                    "monthly_cost": Decimal("20.00"),
                    "currency": "USD",
                    "metadata": {
                        "name": entry.get("name"),
                        "source": "manual_import",
                    },
                }
            )

        return licenses

    async def remove_member(self, email: str) -> dict[str, Any]:
        """Remove a member from the Cursor team.

        This is an Enterprise-only feature. Uses POST /teams/remove-member.

        Args:
            email: Email address of the member to remove

        Returns:
            Dict with success status and message

        Raises:
            ValueError: If the API call fails or feature is not available
        """
        if not self.api_key:
            raise ValueError("API key is required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/teams/remove-member",
                    auth=self._get_auth(),
                    json={"email": email},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": f"Successfully removed {email} from Cursor team",
                    }
                elif response.status_code == 401:
                    raise ValueError("Invalid API key")
                elif response.status_code == 403:
                    raise ValueError("Enterprise feature not available or insufficient permissions")
                elif response.status_code == 404:
                    raise ValueError(f"Member {email} not found in team")
                else:
                    error_msg = response.text or f"API error: {response.status_code}"
                    raise ValueError(error_msg)

        except httpx.RequestError as e:
            raise ValueError(f"Connection error: {str(e)}")

    @staticmethod
    def parse_csv(csv_content: str) -> list[dict[str, Any]]:
        """Parse CSV content into manual data format.

        Expected CSV format:
        email,name,plan
        user@example.com,User Name,Pro

        Args:
            csv_content: CSV string

        Returns:
            List of user dicts for manual_data
        """
        import csv
        from io import StringIO

        users = []
        reader = csv.DictReader(StringIO(csv_content))

        for row in reader:
            users.append(
                {
                    "email": row.get("email", "").strip(),
                    "name": row.get("name", "").strip(),
                    "plan": row.get("plan", "Pro").strip(),
                }
            )

        return users
