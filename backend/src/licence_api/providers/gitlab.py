"""GitLab provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class GitLabProvider(BaseProvider):
    """GitLab integration.

    For self-hosted GitLab (base_url provided):
        - Fetches ALL instance users via /api/v4/users
        - Requires admin token for email access
        - No group_id needed

    For gitlab.com:
        - Fetches group members via /api/v4/groups/:id/members/all
        - Requires group_id
    """

    DEFAULT_BASE_URL = "https://gitlab.com/api/v4"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize GitLab provider."""
        super().__init__(credentials)
        self.access_token = credentials.get("access_token")
        self.group_id = credentials.get("group_id")
        base_url = credentials.get("base_url", "").strip().rstrip("/")

        # Normalize URL
        if base_url:
            base_url = base_url.removeprefix("https://").removeprefix("http://")
            self.base_url = f"https://{base_url}/api/v4"
            self.is_self_hosted = True
        else:
            self.base_url = self.DEFAULT_BASE_URL
            self.is_self_hosted = False

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "PRIVATE-TOKEN": self.access_token,
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test GitLab API connection."""
        try:
            async with httpx.AsyncClient() as client:
                if self.is_self_hosted:
                    # Test with users endpoint for self-hosted
                    response = await client.get(
                        f"{self.base_url}/users",
                        headers=self._get_headers(),
                        params={"per_page": 1},
                        timeout=10.0,
                    )
                else:
                    # Test with group endpoint for gitlab.com
                    if not self.group_id:
                        return False
                    response = await client.get(
                        f"{self.base_url}/groups/{self.group_id}",
                        headers=self._get_headers(),
                        timeout=10.0,
                    )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch users from GitLab.

        For self-hosted: fetches all instance users
        For gitlab.com: fetches group members
        """
        if self.is_self_hosted:
            return await self._fetch_all_instance_users()
        else:
            return await self._fetch_group_members()

    async def _fetch_all_instance_users(self) -> list[dict[str, Any]]:
        """Fetch all users from self-hosted GitLab instance."""
        licenses = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/users",
                    headers=self._get_headers(),
                    params={"per_page": per_page, "page": page},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"Failed to fetch users page {page}: {response.status_code}")
                    break

                users = response.json()
                if not users:
                    break

                for user in users:
                    user_id = user.get("id")
                    username = user.get("username")
                    state = user.get("state", "active")
                    is_bot = user.get("bot", False)

                    # Skip bot accounts
                    if is_bot:
                        continue

                    # Get email
                    email = (
                        user.get("email")
                        or user.get("commit_email")
                        or user.get("public_email")
                    )

                    # Determine status
                    status = "active" if state == "active" else "suspended"

                    # Parse dates
                    created_at = None
                    if user.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(
                                user["created_at"].replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    last_activity = None
                    if user.get("last_activity_on"):
                        try:
                            last_activity = datetime.fromisoformat(
                                f"{user['last_activity_on']}T00:00:00+00:00"
                            )
                        except Exception:
                            pass

                    # Use email for HRIS matching, fall back to username
                    external_id = email.lower() if email else username

                    # Determine license type based on admin status
                    is_admin = user.get("is_admin", False)
                    license_type = "GitLab Admin" if is_admin else "GitLab User"

                    licenses.append({
                        "external_user_id": external_id,
                        "email": email.lower() if email else None,
                        "license_type": license_type,
                        "status": status,
                        "assigned_at": created_at,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "gitlab_id": user_id,
                            "username": username,
                            "name": user.get("name"),
                            "avatar_url": user.get("avatar_url"),
                            "state": state,
                            "web_url": user.get("web_url"),
                            "is_admin": is_admin,
                            "is_using_seat": user.get("using_license_seat", True),
                            "two_factor_enabled": user.get("two_factor_enabled", False),
                        },
                    })

                logger.info(f"Fetched page {page} with {len(users)} users")

                if len(users) < per_page:
                    break

                page += 1

        logger.info(f"Total GitLab users fetched: {len(licenses)}")
        return licenses

    async def _fetch_group_members(self) -> list[dict[str, Any]]:
        """Fetch group members from gitlab.com."""
        if not self.group_id:
            logger.error("group_id is required for gitlab.com")
            return []

        licenses = []
        page = 1
        per_page = 100

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/groups/{self.group_id}/members/all",
                    headers=self._get_headers(),
                    params={"per_page": per_page, "page": page},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error(f"Failed to fetch members page {page}: {response.status_code}")
                    break

                members = response.json()
                if not members:
                    break

                for member in members:
                    username = member.get("username")
                    user_id = member.get("id")

                    # Get detailed user info for email
                    user_data = {}
                    try:
                        user_response = await client.get(
                            f"{self.base_url}/users/{user_id}",
                            headers=self._get_headers(),
                            timeout=10.0,
                        )
                        if user_response.status_code == 200:
                            user_data = user_response.json()
                    except Exception as e:
                        logger.debug(f"Could not fetch user {user_id}: {e}")

                    access_level = member.get("access_level", 0)
                    license_type = self._get_license_type(access_level)

                    state = member.get("state", "active")
                    status = "active" if state == "active" else "suspended"

                    created_at = None
                    if user_data.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(
                                user_data["created_at"].replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    last_activity = None
                    if user_data.get("last_activity_on"):
                        try:
                            last_activity = datetime.fromisoformat(
                                f"{user_data['last_activity_on']}T00:00:00+00:00"
                            )
                        except Exception:
                            pass

                    email = (
                        user_data.get("email")
                        or user_data.get("commit_email")
                        or user_data.get("public_email")
                        or member.get("email")
                    )

                    external_id = email.lower() if email else username

                    licenses.append({
                        "external_user_id": external_id,
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
                        },
                    })

                if len(members) < per_page:
                    break

                page += 1

        logger.info(f"Total GitLab members fetched: {len(licenses)}")
        return licenses

    def _get_access_level_name(self, level: int) -> str:
        """Convert access level to name."""
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
        """Convert access level to license type."""
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
