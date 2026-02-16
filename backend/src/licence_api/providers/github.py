"""GitHub provider integration."""

from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

from licence_api.providers.base import BaseProvider


class GitHubProvider(BaseProvider):
    """GitHub organization member integration."""

    BASE_URL = "https://api.github.com"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize GitHub provider.

        Args:
            credentials: Dict with keys:
                - access_token: Personal access token or GitHub App token
                - org_name: GitHub organization name
        """
        super().__init__(credentials)
        self.access_token = credentials.get("access_token")
        self.org_name = credentials.get("org_name")

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def test_connection(self) -> bool:
        """Test GitHub API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/orgs/{quote(self.org_name, safe='')}",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all organization members from GitHub.

        Returns:
            List of license data dicts
        """
        licenses = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient() as client:
            # Fetch organization members
            while True:
                response = await client.get(
                    f"{self.BASE_URL}/orgs/{quote(self.org_name, safe='')}/members",
                    headers=self._get_headers(),
                    params={"per_page": per_page, "page": page},
                    timeout=30.0,
                )
                response.raise_for_status()
                members = response.json()

                if not members:
                    break

                # Fetch detailed user info for each member
                for member in members:
                    username = member.get("login")

                    # Get user details including email
                    user_response = await client.get(
                        f"{self.BASE_URL}/users/{quote(username, safe='')}",
                        headers=self._get_headers(),
                        timeout=10.0,
                    )

                    user_data = {}
                    if user_response.status_code == 200:
                        user_data = user_response.json()

                    # Get membership details
                    membership_response = await client.get(
                        f"{self.BASE_URL}/orgs/{quote(self.org_name, safe='')}/memberships/{quote(username, safe='')}",
                        headers=self._get_headers(),
                        timeout=10.0,
                    )

                    role = "member"
                    if membership_response.status_code == 200:
                        membership_data = membership_response.json()
                        role = membership_data.get("role", "member")

                    # Determine license type based on role
                    license_type = "GitHub Organization Member"
                    if role == "admin":
                        license_type = "GitHub Organization Admin"

                    # Parse dates
                    created_at = None
                    if user_data.get("created_at"):
                        created_at = datetime.fromisoformat(
                            user_data["created_at"].replace("Z", "+00:00")
                        )

                    updated_at = None
                    if user_data.get("updated_at"):
                        updated_at = datetime.fromisoformat(
                            user_data["updated_at"].replace("Z", "+00:00")
                        )

                    # Use email if available, otherwise use username
                    email = user_data.get("email") or f"{username}@github.com"

                    licenses.append(
                        {
                            "external_user_id": username,
                            "email": email.lower() if email else None,
                            "license_type": license_type,
                            "status": "active",
                            "assigned_at": created_at,
                            "last_activity_at": updated_at,
                            "metadata": {
                                "github_id": member.get("id"),
                                "username": username,
                                "name": user_data.get("name"),
                                "avatar_url": member.get("avatar_url"),
                                "role": role,
                                "two_factor_enabled": member.get("two_factor_authentication"),
                                "company": user_data.get("company"),
                                "location": user_data.get("location"),
                            },
                        }
                    )

                page += 1

        return licenses
