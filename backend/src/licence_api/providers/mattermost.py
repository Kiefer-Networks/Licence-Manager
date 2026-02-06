"""Mattermost provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class MattermostProvider(BaseProvider):
    """Mattermost user integration."""

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Mattermost provider.

        Args:
            credentials: Dict with keys:
                - access_token: Personal access token or bot token
                - server_url: Mattermost server URL (e.g., https://mattermost.company.com)
        """
        super().__init__(credentials)
        self.access_token = credentials.get("access_token")
        server_url = credentials.get("server_url", "").rstrip("/")
        self.base_url = f"{server_url}/api/v4" if server_url else ""
        self._license_info: dict[str, Any] | None = None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Mattermost API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/me",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def get_license_info(self) -> dict[str, Any] | None:
        """Fetch Mattermost license information.

        Returns:
            License info dict or None if not available
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/license/client?format=old",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()

                    # Parse expiration timestamp (milliseconds)
                    expires_at = None
                    if data.get("ExpiresAt"):
                        try:
                            expires_at = datetime.fromtimestamp(
                                int(data["ExpiresAt"]) / 1000
                            ).isoformat()
                        except (ValueError, TypeError):
                            pass

                    # Parse start timestamp
                    starts_at = None
                    if data.get("StartsAt"):
                        try:
                            starts_at = datetime.fromtimestamp(
                                int(data["StartsAt"]) / 1000
                            ).isoformat()
                        except (ValueError, TypeError):
                            pass

                    return {
                        "is_licensed": data.get("IsLicensed") == "true",
                        "is_trial": data.get("IsTrial") == "true",
                        "license_id": data.get("Id"),
                        "sku_name": data.get("SkuShortName") or data.get("SkuName"),
                        "company": data.get("Company"),
                        "licensee_name": data.get("Name"),
                        "licensee_email": data.get("Email"),
                        "max_users": int(data.get("Users", 0)) if data.get("Users") else None,
                        "starts_at": starts_at,
                        "expires_at": expires_at,
                        "features": {
                            "ldap": data.get("LDAP") == "true",
                            "saml": data.get("SAML") == "true",
                            "mfa": data.get("MFA") == "true",
                            "guest_accounts": data.get("GuestAccounts") == "true",
                            "compliance": data.get("Compliance") == "true",
                            "data_retention": data.get("DataRetention") == "true",
                            "elasticsearch": data.get("Elasticsearch") == "true",
                            "cluster": data.get("Cluster") == "true",
                        },
                    }
        except Exception:
            pass
        return None

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users from Mattermost.

        Returns:
            List of license data dicts
        """
        # Fetch license info first
        self._license_info = await self.get_license_info()

        licenses = []
        page = 0
        per_page = 200

        async with httpx.AsyncClient() as client:
            # Get team info first to enrich user data
            teams_map = await self._get_teams_map(client)

            while True:
                response = await client.get(
                    f"{self.base_url}/users",
                    headers=self._get_headers(),
                    params={
                        "page": page,
                        "per_page": per_page,
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                users = response.json()

                if not users:
                    break

                for user in users:
                    # Skip bots and deactivated system accounts
                    if user.get("is_bot"):
                        continue

                    email = user.get("email", "")
                    username = user.get("username", "")

                    # Determine status
                    delete_at = user.get("delete_at", 0)
                    if delete_at > 0:
                        status = "suspended"
                    else:
                        status = "active"

                    # Determine license type based on roles
                    roles = user.get("roles", "")
                    license_type = self._get_license_type(roles)

                    # Parse dates (Mattermost uses milliseconds)
                    created_at = None
                    if user.get("create_at"):
                        created_at = datetime.fromtimestamp(user["create_at"] / 1000).replace(
                            tzinfo=None
                        )

                    last_activity = None
                    if user.get("last_activity_at"):
                        last_activity = datetime.fromtimestamp(
                            user["last_activity_at"] / 1000
                        ).replace(tzinfo=None)

                    # Get user's teams
                    user_teams = await self._get_user_teams(client, user.get("id"))
                    team_names = [teams_map.get(t, t) for t in user_teams]

                    licenses.append(
                        {
                            "external_user_id": email.lower() if email else username,
                            "email": email.lower() if email else None,
                            "license_type": license_type,
                            "status": status,
                            "assigned_at": created_at,
                            "last_activity_at": last_activity,
                            "metadata": {
                                "mattermost_id": user.get("id"),
                                "username": username,
                                "name": (
                                    f"{user.get('first_name', '')} "
                                    f"{user.get('last_name', '')}".strip()
                                    or user.get("nickname")
                                ),
                                "nickname": user.get("nickname"),
                                "position": user.get("position"),
                                "roles": roles,
                                "locale": user.get("locale"),
                                "timezone": user.get("timezone"),
                                "teams": team_names,
                                "auth_service": user.get("auth_service"),
                                "mfa_active": user.get("mfa_active", False),
                            },
                        }
                    )

                page += 1

        return licenses

    async def _get_teams_map(self, client: httpx.AsyncClient) -> dict[str, str]:
        """Get mapping of team IDs to team names.

        Args:
            client: HTTP client

        Returns:
            Dict mapping team ID to team display name
        """
        teams_map = {}
        try:
            response = await client.get(
                f"{self.base_url}/teams",
                headers=self._get_headers(),
                params={"page": 0, "per_page": 200},
                timeout=10.0,
            )
            if response.status_code == 200:
                teams = response.json()
                for team in teams:
                    teams_map[team.get("id")] = team.get("display_name") or team.get("name")
        except Exception:
            pass
        return teams_map

    async def _get_user_teams(self, client: httpx.AsyncClient, user_id: str) -> list[str]:
        """Get teams for a user.

        Args:
            client: HTTP client
            user_id: Mattermost user ID

        Returns:
            List of team IDs
        """
        try:
            response = await client.get(
                f"{self.base_url}/users/{user_id}/teams",
                headers=self._get_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                teams = response.json()
                return [t.get("id") for t in teams]
        except Exception:
            pass
        return []

    def _get_license_type(self, roles: str) -> str:
        """Convert roles to license type.

        Args:
            roles: Space-separated role names

        Returns:
            License type string
        """
        roles_lower = roles.lower()
        if "system_admin" in roles_lower:
            return "Mattermost System Admin"
        elif "team_admin" in roles_lower:
            return "Mattermost Team Admin"
        elif "channel_admin" in roles_lower:
            return "Mattermost Channel Admin"
        elif "system_user" in roles_lower or "user" in roles_lower:
            return "Mattermost User"
        elif "system_guest" in roles_lower or "guest" in roles_lower:
            return "Mattermost Guest"
        else:
            return "Mattermost User"

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get provider metadata including license info.

        Should be called after fetch_licenses().

        Returns:
            Provider metadata dict or None
        """
        return self._license_info
