"""Miro provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class MiroProvider(BaseProvider):
    """Miro team member integration."""

    BASE_URL = "https://api.miro.com/v2"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Miro provider.

        Args:
            credentials: Dict with keys:
                - access_token: Miro OAuth access token
                - org_id: Optional organization ID (for enterprise)
        """
        super().__init__(credentials)
        self.access_token = credentials.get("access_token")
        self.org_id = credentials.get("org_id")

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Miro API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Test with getting current user/token info
                response = await client.get(
                    f"{self.BASE_URL}/oauth/token",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                # Also try organizations endpoint
                if response.status_code != 200:
                    response = await client.get(
                        f"{self.BASE_URL}/orgs",
                        headers=self._get_headers(),
                        timeout=10.0,
                    )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all team members from Miro.

        Returns:
            List of license data dicts
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # First, get organization info if org_id provided
            if self.org_id:
                # Enterprise API - get organization members
                licenses = await self._fetch_org_members(client)
            else:
                # Team API - get all teams and their members
                licenses = await self._fetch_team_members(client)

        return licenses

    async def _fetch_org_members(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch members from organization (Enterprise).

        Args:
            client: HTTP client

        Returns:
            List of license data dicts
        """
        licenses = []
        cursor = None

        while True:
            params: dict[str, Any] = {"limit": 100}
            if cursor:
                params["cursor"] = cursor

            response = await client.get(
                f"{self.BASE_URL}/orgs/{self.org_id}/members",
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for member in data.get("data", []):
                user = member.get("user", {})
                email = user.get("email", "")

                # Determine license type from role
                role = member.get("role", "member")
                license_type = self._get_license_type(role)

                # Parse dates
                created_at = None
                if member.get("createdAt"):
                    created_at = datetime.fromisoformat(member["createdAt"].replace("Z", "+00:00"))

                modified_at = None
                if member.get("modifiedAt"):
                    modified_at = datetime.fromisoformat(
                        member["modifiedAt"].replace("Z", "+00:00")
                    )

                licenses.append(
                    {
                        "external_user_id": email.lower() if email else user.get("id"),
                        "email": email.lower() if email else None,
                        "license_type": license_type,
                        "status": "active" if member.get("active", True) else "suspended",
                        "assigned_at": created_at,
                        "last_activity_at": modified_at,
                        "metadata": {
                            "miro_id": user.get("id"),
                            "name": user.get("name"),
                            "role": role,
                            "license": member.get("license"),
                        },
                    }
                )

            # Check for next page
            cursor = data.get("cursor")
            if not cursor or not data.get("data"):
                break

        return licenses

    async def _fetch_team_members(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch members from teams (non-Enterprise).

        Args:
            client: HTTP client

        Returns:
            List of license data dicts
        """
        licenses = []
        seen_users = set()

        # Get all teams first
        teams_response = await client.get(
            f"{self.BASE_URL}/teams",
            headers=self._get_headers(),
            timeout=30.0,
        )

        if teams_response.status_code != 200:
            return licenses

        teams_data = teams_response.json()

        for team in teams_data.get("data", []):
            team_id = team.get("id")
            cursor = None

            while True:
                params: dict[str, Any] = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(
                    f"{self.BASE_URL}/teams/{team_id}/members",
                    headers=self._get_headers(),
                    params=params,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    break

                data = response.json()

                for member in data.get("data", []):
                    user_id = member.get("id")

                    # Skip if already seen
                    if user_id in seen_users:
                        continue
                    seen_users.add(user_id)

                    email = member.get("email", "")
                    role = member.get("role", "member")
                    license_type = self._get_license_type(role)

                    licenses.append(
                        {
                            "external_user_id": email.lower() if email else str(user_id),
                            "email": email.lower() if email else None,
                            "license_type": license_type,
                            "status": "active",
                            "metadata": {
                                "miro_id": user_id,
                                "name": member.get("name"),
                                "role": role,
                                "team_id": team_id,
                                "team_name": team.get("name"),
                            },
                        }
                    )

                # Check for next page
                cursor = data.get("cursor")
                if not cursor or not data.get("data"):
                    break

        return licenses

    def _get_license_type(self, role: str) -> str:
        """Convert role to license type.

        Args:
            role: Miro role name

        Returns:
            License type string
        """
        role_mapping = {
            "organization_admin": "Miro Organization Admin",
            "organization_team_admin": "Miro Team Admin",
            "team_admin": "Miro Team Admin",
            "admin": "Miro Admin",
            "member": "Miro Member",
            "guest": "Miro Guest",
            "viewer": "Miro Viewer",
        }
        return role_mapping.get(role.lower(), f"Miro {role.title()}")
