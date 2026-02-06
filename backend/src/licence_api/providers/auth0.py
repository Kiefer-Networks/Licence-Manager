"""Auth0 identity provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class Auth0Provider(BaseProvider):
    """Auth0 identity provider integration.

    Fetches users from Auth0 Management API to track identity licenses.
    Auth0 pricing is typically based on Monthly Active Users (MAU) or
    total users depending on the plan.

    Credentials required:
        - domain: Auth0 tenant domain (e.g., 'your-tenant.auth0.com')
        - client_id: Management API client ID
        - client_secret: Management API client secret
    """

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Auth0 provider."""
        super().__init__(credentials)
        self.domain = credentials.get("domain", "").rstrip("/")
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get Management API access token using client credentials.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://{self.domain}/oauth/token",
                json={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": f"https://{self.domain}/api/v2/",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    def _get_headers(self, token: str) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Auth0 Management API connection.

        Returns:
            True if connection is successful
        """
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                # Test by fetching tenant settings
                response = await client.get(
                    f"https://{self.domain}/api/v2/tenants/settings",
                    headers=self._get_headers(token),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Auth0 connection test failed: {e}")
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users from Auth0.

        Auth0 users represent identity licenses. Each user consumes
        a license slot based on your Auth0 plan (MAU or total users).

        Returns:
            List of license data dicts
        """
        licenses = []
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            page = 0
            per_page = 100

            while True:
                response = await client.get(
                    f"https://{self.domain}/api/v2/users",
                    headers=self._get_headers(token),
                    params={
                        "page": page,
                        "per_page": per_page,
                        "include_totals": "true",
                        "fields": (
                            "user_id,email,name,created_at,last_login,"
                            "blocked,email_verified,identities"
                        ),
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                users = data.get("users", data) if isinstance(data, dict) else data

                for user in users:
                    # Determine license type based on connection/identity
                    identities = user.get("identities", [])
                    connection = (
                        identities[0].get("connection", "unknown") if identities else "unknown"
                    )

                    # Map connection to license type
                    if connection in ["Username-Password-Authentication", "email"]:
                        license_type = "Database"
                    elif connection in ["google-oauth2", "google-apps"]:
                        license_type = "Social (Google)"
                    elif connection in ["github", "linkedin", "twitter"]:
                        license_type = f"Social ({connection})"
                    elif "saml" in connection.lower() or "adfs" in connection.lower():
                        license_type = "Enterprise (SAML)"
                    elif "waad" in connection.lower() or "azure" in connection.lower():
                        license_type = "Enterprise (Azure AD)"
                    else:
                        license_type = connection

                    # Parse dates
                    created_at = None
                    if user.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(
                                user["created_at"].replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    last_login = None
                    if user.get("last_login"):
                        try:
                            last_login = datetime.fromisoformat(
                                user["last_login"].replace("Z", "+00:00")
                            )
                        except Exception:
                            pass

                    # Determine status
                    status = "active"
                    if user.get("blocked"):
                        status = "blocked"

                    licenses.append(
                        {
                            "external_user_id": user.get("email") or user.get("user_id"),
                            "email": user.get("email"),
                            "license_type": license_type,
                            "status": status,
                            "assigned_at": created_at,
                            "last_activity_at": last_login,
                            "metadata": {
                                "user_id": user.get("user_id"),
                                "name": user.get("name"),
                                "email_verified": user.get("email_verified"),
                                "connection": connection,
                            },
                        }
                    )

                # Check pagination
                total = data.get("total", len(users)) if isinstance(data, dict) else len(users)
                if len(users) < per_page or (page + 1) * per_page >= total:
                    break
                page += 1

        logger.info(f"Fetched {len(licenses)} users from Auth0")
        return licenses

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get Auth0 tenant metadata.

        Returns:
            Dict with tenant info or None
        """
        return {
            "domain": self.domain,
            "provider_type": "identity",
        }
