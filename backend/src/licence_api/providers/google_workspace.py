"""Google Workspace provider integration."""

import json
import logging
import time
from datetime import datetime
from typing import Any

import httpx
from jose import jwt

from licence_api.config import get_settings
from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Google Workspace SKU ID → human-readable name mapping
GOOGLE_WORKSPACE_SKUS: dict[str, str] = {
    "Google-Apps-Lite": "Google Workspace Business Starter",
    "Google-Apps-For-Business": "Google Workspace Business Standard",
    "Google-Apps-Unlimited": "Google Workspace Business Plus",
    "1010020027": "Google Workspace Enterprise Starter",
    "1010020020": "Google Workspace Enterprise Standard",
    "1010020025": "Google Workspace Enterprise Plus",
    "1010020028": "Google Workspace Frontline Starter",
    "1010020029": "Google Workspace Frontline Standard",
    "1010060001": "Google Workspace Essentials",
    "1010060003": "Google Workspace Essentials Plus",
    "1010010001": "Google Workspace for Education Fundamentals",
    "1010370001": "Google Workspace for Education Standard",
    "1010310002": "Google Workspace for Education Plus",
    "1010310003": "Google Workspace for Education Teaching and Learning Upgrade",
}


class GoogleWorkspaceProvider(BaseProvider):
    """Google Workspace integration for user licenses."""

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Google Workspace provider.

        Args:
            credentials: Dict with keys:
                Service Account mode:
                - service_account_json: Service account JSON key (as string)
                - admin_email: Admin email for domain-wide delegation
                - domain: Google Workspace domain

                OAuth mode:
                - refresh_token: OAuth2 refresh token
                - admin_email: Admin email (extracted from OAuth)
                - domain: Google Workspace domain (extracted from hd claim)
        """
        super().__init__(credentials)
        self.refresh_token = credentials.get("refresh_token")
        self.service_account = json.loads(
            credentials.get("service_account_json")
            or credentials.get("google_service_account_json", "{}")
        )
        self.admin_email = credentials.get("admin_email") or credentials.get("google_admin_email")
        self.domain = credentials.get("domain") or credentials.get("google_domain")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using refresh token or service account.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        if self.refresh_token:
            return await self._refresh_oauth_token()
        else:
            return await self._get_service_account_token()

    async def _refresh_oauth_token(self) -> str:
        """Get access token by refreshing OAuth2 token.

        Returns:
            Access token string
        """
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def _get_service_account_token(self) -> str:
        """Get access token using service account JWT.

        Returns:
            Access token string
        """
        now = int(time.time())
        payload = {
            "iss": self.service_account["client_email"],
            "sub": self.admin_email,
            "scope": "https://www.googleapis.com/auth/admin.directory.user.readonly https://www.googleapis.com/auth/apps.licensing.readonly",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + 3600,
        }

        signed_jwt = jwt.encode(
            payload,
            self.service_account["private_key"],
            algorithm="RS256",
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt,
                },
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def test_connection(self) -> bool:
        """Test Google Workspace API connection.

        Returns:
            True if connection is successful
        """
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://admin.googleapis.com/admin/directory/v1/users",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"domain": self.domain, "maxResults": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _fetch_license_assignments(self, client: httpx.AsyncClient, token: str) -> dict[str, str]:
        """Fetch license SKU assignments from Google Licensing API.

        Returns:
            Dict mapping user email → human-readable license type name.
        """
        license_map: dict[str, str] = {}
        try:
            page_token = None
            while True:
                params: dict[str, Any] = {
                    "customerId": "my_customer",
                    "maxResults": 1000,
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    "https://licensing.googleapis.com/apps/licensing/v1/product/Google-Apps/users",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                    timeout=30.0,
                )
                if response.status_code != 200:
                    logger.warning("Licensing API unavailable (%s), falling back to generic type", response.status_code)
                    return license_map
                data = response.json()

                for item in data.get("items", []):
                    user_id = item.get("userId", "").lower()
                    sku_id = item.get("skuId", "")
                    license_map[user_id] = GOOGLE_WORKSPACE_SKUS.get(sku_id, f"Google Workspace ({sku_id})")

                page_token = data.get("nextPageToken")
                if not page_token:
                    break
        except Exception:
            logger.warning("Failed to fetch license assignments, using generic type", exc_info=True)

        return license_map

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users with licenses from Google Workspace.

        Returns:
            List of license data dicts
        """
        token = await self._get_access_token()
        licenses = []
        page_token = None

        async with httpx.AsyncClient() as client:
            # Try to get actual license types from Licensing API
            license_map = await self._fetch_license_assignments(client, token)

            while True:
                params: dict[str, Any] = {
                    "domain": self.domain,
                    "maxResults": 500,
                }
                if page_token:
                    params["pageToken"] = page_token

                response = await client.get(
                    "https://admin.googleapis.com/admin/directory/v1/users",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                for user in data.get("users", []):
                    # Skip suspended users
                    if user.get("suspended"):
                        user_status = "suspended"
                    else:
                        user_status = "active"

                    # Parse last login time
                    last_activity = None
                    if (
                        user.get("lastLoginTime")
                        and user["lastLoginTime"] != "1970-01-01T00:00:00.000Z"
                    ):
                        last_activity = datetime.fromisoformat(
                            user["lastLoginTime"].replace("Z", "+00:00")
                        )

                    # Parse creation time
                    created_at = None
                    if user.get("creationTime"):
                        created_at = datetime.fromisoformat(
                            user["creationTime"].replace("Z", "+00:00")
                        )

                    email = user["primaryEmail"].lower()
                    license_type = license_map.get(email, "Google Workspace")

                    licenses.append(
                        {
                            "external_user_id": email,
                            "email": email,
                            "license_type": license_type,
                            "status": user_status,
                            "assigned_at": created_at,
                            "last_activity_at": last_activity,
                            "metadata": {
                                "name": user.get("name", {}).get("fullName"),
                                "org_unit": user.get("orgUnitPath"),
                                "is_admin": user.get("isAdmin", False),
                            },
                        }
                    )

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return licenses
