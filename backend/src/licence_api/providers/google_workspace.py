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

# Google product IDs to query for license assignments
GOOGLE_PRODUCT_IDS = [
    "Google-Apps",  # Google Workspace (main)
    "101031",       # Google Workspace Additional Storage
    "101037",       # Gemini for Google Workspace
]

# Google Workspace SKU ID → human-readable name mapping
GOOGLE_WORKSPACE_SKUS: dict[str, str] = {
    # Google Workspace core plans
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
    # Education
    "1010010001": "Google Workspace for Education Fundamentals",
    "1010370001": "Google Workspace for Education Standard",
    "1010310002": "Google Workspace for Education Plus",
    "1010310003": "Google Workspace for Education Teaching and Learning Upgrade",
    # Gemini / AI add-ons
    "1010470001": "Gemini Business",
    "1010470003": "Gemini Enterprise",
    "1010470004": "Gemini AI Meetings and Messaging",
    # Additional Storage
    "Google-Apps-Extra-Storage": "Google Workspace Additional Storage",
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
        """Get OAuth access token using refresh token or service account."""
        if self._access_token:
            return self._access_token

        if self.refresh_token:
            return await self._refresh_oauth_token()
        else:
            return await self._get_service_account_token()

    async def _refresh_oauth_token(self) -> str:
        """Get access token by refreshing OAuth2 token."""
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
        """Get access token using service account JWT."""
        now = int(time.time())
        payload = {
            "iss": self.service_account["client_email"],
            "sub": self.admin_email,
            "scope": (
                "https://www.googleapis.com/auth/admin.directory.user.readonly "
                "https://www.googleapis.com/auth/apps.licensing"
            ),
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
        """Test Google Workspace API connection."""
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

    async def _fetch_all_users(
        self, client: httpx.AsyncClient, token: str,
    ) -> dict[str, dict[str, Any]]:
        """Fetch all users from Directory API for enrichment.

        Returns:
            Dict mapping email → user details (name, lastLogin, etc.)
        """
        users: dict[str, dict[str, Any]] = {}
        page_token = None

        while True:
            params: dict[str, Any] = {"domain": self.domain, "maxResults": 500}
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
                email = user["primaryEmail"].lower()
                users[email] = user

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return users

    async def _fetch_license_assignments(
        self, client: httpx.AsyncClient, token: str,
    ) -> list[dict[str, str]]:
        """Fetch all license assignments from Google Licensing API.

        Queries multiple product IDs to capture all license types
        (Workspace, Gemini, Storage, etc.).

        Returns:
            List of dicts with userId (email), skuId, productId, license_type.
        """
        assignments: list[dict[str, str]] = []

        for product_id in GOOGLE_PRODUCT_IDS:
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
                        f"https://licensing.googleapis.com/apps/licensing/v1/product/{product_id}/users",
                        headers={"Authorization": f"Bearer {token}"},
                        params=params,
                        timeout=30.0,
                    )
                    if response.status_code == 403:
                        logger.info("Licensing API not authorized for product %s, skipping", product_id)
                        break
                    if response.status_code == 404:
                        break
                    if response.status_code != 200:
                        logger.warning("Licensing API error for product %s: %s", product_id, response.status_code)
                        break

                    data = response.json()
                    for item in data.get("items", []):
                        sku_id = item.get("skuId", "")
                        assignments.append({
                            "userId": item.get("userId", "").lower(),
                            "skuId": sku_id,
                            "productId": product_id,
                            "license_type": GOOGLE_WORKSPACE_SKUS.get(
                                sku_id, f"Google Workspace ({sku_id})"
                            ),
                        })

                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
            except Exception:
                logger.warning("Failed to query Licensing API for product %s", product_id, exc_info=True)

        return assignments

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all license assignments from Google Workspace.

        Primary source: Licensing API (real license assignments per user/SKU).
        Fallback: Directory API users (all get generic "Google Workspace" type).
        Directory API is always used to enrich with user details.

        Returns:
            List of license data dicts
        """
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            # Always fetch users for enrichment (name, last login, status)
            users_map = await self._fetch_all_users(client, token)

            # Try Licensing API for real license assignments
            assignments = await self._fetch_license_assignments(client, token)

            if assignments:
                return self._build_from_assignments(assignments, users_map)
            else:
                # Fallback: all users get generic "Google Workspace"
                logger.info("Licensing API returned no data, falling back to Directory API users")
                return self._build_from_users(users_map)

    def _build_from_assignments(
        self,
        assignments: list[dict[str, str]],
        users_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build license list from Licensing API assignments enriched with user data."""
        licenses = []

        for assignment in assignments:
            email = assignment["userId"]
            user = users_map.get(email, {})

            licenses.append(self._build_license_entry(
                email=email,
                license_type=assignment["license_type"],
                user=user,
            ))

        return licenses

    def _build_from_users(
        self, users_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build license list from Directory API users (fallback)."""
        return [
            self._build_license_entry(email=email, license_type="Google Workspace", user=user)
            for email, user in users_map.items()
        ]

    def _build_license_entry(
        self, email: str, license_type: str, user: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a single license entry from user data."""
        if user.get("suspended"):
            status = "suspended"
        else:
            status = "active" if user else "active"

        last_activity = None
        if (
            user.get("lastLoginTime")
            and user["lastLoginTime"] != "1970-01-01T00:00:00.000Z"
        ):
            last_activity = datetime.fromisoformat(
                user["lastLoginTime"].replace("Z", "+00:00")
            )

        created_at = None
        if user.get("creationTime"):
            created_at = datetime.fromisoformat(
                user["creationTime"].replace("Z", "+00:00")
            )

        return {
            "external_user_id": email,
            "email": email,
            "license_type": license_type,
            "status": status,
            "assigned_at": created_at,
            "last_activity_at": last_activity,
            "metadata": {
                "name": user.get("name", {}).get("fullName") if user else None,
                "org_unit": user.get("orgUnitPath") if user else None,
                "is_admin": user.get("isAdmin", False) if user else False,
            },
        }
