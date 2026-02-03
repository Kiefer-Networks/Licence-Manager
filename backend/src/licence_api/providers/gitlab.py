"""GitLab provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class GitLabProvider(BaseProvider):
    """GitLab group member integration."""

    DEFAULT_BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize GitLab provider.

        Args:
            credentials: Dict with keys:
                - access_token: Personal access token or group token
                - group_id: GitLab group ID or path
                - base_url: Optional custom GitLab URL (for self-hosted)
        """
        super().__init__(credentials)
        self.access_token = credentials.get("access_token")
        self.group_id = credentials.get("group_id")
        base_url = credentials.get("base_url", "").strip().rstrip("/")
        # Normalize: ensure https:// prefix, handle user input with/without protocol
        if base_url:
            base_url = base_url.removeprefix("https://").removeprefix("http://")
            self.base_url = f"https://{base_url}/api/v4"
        else:
            self.base_url = self.DEFAULT_BASE_URL

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "PRIVATE-TOKEN": self.access_token,
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test GitLab API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/groups/{self.group_id}",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all group members from GitLab.

        Returns:
            List of license data dicts
        """
        licenses = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient() as client:
            # Fetch group members with inherited members
            while True:
                response = await client.get(
                    f"{self.base_url}/groups/{self.group_id}/members/all",
                    headers=self._get_headers(),
                    params={"per_page": per_page, "page": page},
                    timeout=30.0,
                )
                response.raise_for_status()
                members = response.json()

                if not members:
                    break

                for member in members:
                    username = member.get("username")
                    user_id = member.get("id")

                    # Get detailed user info
                    user_data = {}
                    try:
                        user_response = await client.get(
                            f"{self.base_url}/users/{user_id}",
                            headers=self._get_headers(),
                            timeout=10.0,
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                    except Exception:
                        pass

                    # Map access level to license type
                    access_level = member.get("access_level", 0)
                    license_type = self._get_license_type(access_level)

                    # Determine status
                    state = member.get("state", "active")
                    status = "active" if state == "active" else "suspended"

                    # Parse dates
                    created_at = None
                    if user_data.get("created_at"):
                        created_at = datetime.fromisoformat(
                            user_data["created_at"].replace("Z", "+00:00")
                        )

                    last_activity = None
                    if user_data.get("last_activity_on"):
                        # last_activity_on is date only, not datetime
                        last_activity = datetime.fromisoformat(
                            f"{user_data['last_activity_on']}T00:00:00+00:00"
                        )

                    email = member.get("email") or user_data.get("email") or f"{username}@gitlab.com"

                    licenses.append({
                        "external_user_id": username,
                        "email": email.lower() if email else None,
                        "license_type": license_type,
                        "status": status,
                        "assigned_at": created_at,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "gitlab_id": user_id,
                            "username": username,
                            "name": member.get("name"),
                            "avatar_url": member.get("avatar_url"),
                            "access_level": access_level,
                            "access_level_name": self._get_access_level_name(access_level),
                            "state": state,
                            "web_url": member.get("web_url"),
                            "is_using_seat": user_data.get("is_using_seat"),
                            "bot": user_data.get("bot", False),
                        },
                    })

                page += 1

        return licenses

    def _get_access_level_name(self, level: int) -> str:
        """Convert access level to name.

        Args:
            level: GitLab access level number

        Returns:
            Access level name
        """
        levels = {
            0: "No access",
            5: "Minimal access",
            10: "Guest",
            20: "Reporter",
            30: "Developer",
            40: "Maintainer",
            50: "Owner",
        }
        return levels.get(level, f"Level {level}")

    def _get_license_type(self, access_level: int) -> str:
        """Convert access level to license type.

        Args:
            access_level: GitLab access level number

        Returns:
            License type string
        """
        if access_level >= 50:
            return "GitLab Owner"
        elif access_level >= 40:
            return "GitLab Maintainer"
        elif access_level >= 30:
            return "GitLab Developer"
        elif access_level >= 20:
            return "GitLab Reporter"
        elif access_level >= 10:
            return "GitLab Guest"
        else:
            return "GitLab Member"
