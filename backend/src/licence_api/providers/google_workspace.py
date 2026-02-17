"""Google Workspace provider integration."""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
from jose import jwt

from licence_api.config import get_settings
from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Google product IDs to query for license assignments
# Source: https://developers.google.com/workspace/admin/licensing/v1/how-tos/products
# and https://github.com/taers232c/GAMADV-XTD3/wiki/Licenses
GOOGLE_PRODUCT_IDS = [
    "Google-Apps",                      # Google Workspace (main)
    "101001",                           # Cloud Identity Free
    "101005",                           # Cloud Identity Premium
    "101031",                           # Google Workspace for Education (Standard/Plus)
    "101033",                           # Google Voice
    "101034",                           # Google Workspace Archived User
    "101035",                           # Cloud Search
    "101036",                           # Google Meet Global Dialing
    "101037",                           # Google Workspace for Education (Teaching & Learning)
    "101038",                           # AppSheet
    "101039",                           # Assured Controls
    "101040",                           # Chrome Enterprise
    "101043",                           # Google Workspace Additional Storage
    "101047",                           # Gemini / AI add-ons (AI Ultra, Gemini Business/Enterprise)
    "101049",                           # Education Endpoint Management
    "101050",                           # Colab
    "Google-Vault",                     # Google Vault
    "Google-Drive-storage",             # Google Drive Storage (legacy)
    "Google-Chrome-Device-Management",  # Chrome Device Management (legacy)
]

# Google Workspace SKU ID → human-readable name mapping (fallback if API doesn't return skuName)
GOOGLE_WORKSPACE_SKUS: dict[str, str] = {
    # Google Workspace core plans
    "Google-Apps-Lite": "Google Workspace Business Starter",
    "Google-Apps-For-Business": "Google Workspace Business Standard",
    "Google-Apps-Unlimited": "Google Workspace Business Plus",
    "1010020027": "Google Workspace Business Starter",
    "1010020028": "Google Workspace Business Standard",
    "1010020025": "Google Workspace Business Plus",
    "1010020029": "Google Workspace Enterprise Starter",
    "1010020026": "Google Workspace Enterprise Standard",
    "1010020020": "Google Workspace Enterprise Plus",
    "1010020030": "Google Workspace Frontline Starter",
    "1010020031": "Google Workspace Frontline Standard",
    "1010020034": "Google Workspace Frontline Plus",
    "1010060001": "Google Workspace Essentials",
    "1010060003": "Google Workspace Enterprise Essentials",
    "1010060005": "Google Workspace Enterprise Essentials Plus",
    # Education
    "1010070001": "Google Workspace for Education Fundamentals",
    "1010310002": "Google Workspace for Education Plus (Legacy)",
    "1010310005": "Google Workspace for Education Standard",
    "1010310008": "Google Workspace for Education Plus",
    "1010370001": "Google Workspace for Education: Teaching and Learning Upgrade",
    # Cloud Identity
    "1010010001": "Cloud Identity Free",
    "1010050001": "Cloud Identity Premium",
    # Gemini / AI add-ons
    "1010470001": "Gemini Enterprise",
    "1010470003": "Gemini Business",
    "1010470004": "AI Pro for Education",
    "1010470005": "Gemini Education Premium",
    "1010470006": "AI Security",
    "1010470007": "AI Meetings and Messaging",
    "1010470008": "AI Ultra",
    # Google Voice
    "1010330002": "Google Voice Premier",
    "1010330003": "Google Voice Starter",
    "1010330004": "Google Voice Standard",
    # Google Vault
    "Google-Vault": "Google Vault",
    "Google-Vault-Former-Employee": "Google Vault (Former Employee)",
    # AppSheet
    "1010380001": "AppSheet Core",
    "1010380002": "AppSheet Enterprise Standard",
    "1010380003": "AppSheet Enterprise Plus",
    # Assured Controls
    "1010390001": "Assured Controls",
    "1010390002": "Assured Controls Plus",
    # Chrome Enterprise
    "1010400001": "Chrome Enterprise Premium",
    # Additional Storage
    "1010430001": "Google Workspace Additional Storage",
    "Google-Apps-Extra-Storage": "Google Workspace Additional Storage",
    # Colab
    "1010500001": "Colab Pro",
    "1010500002": "Colab Pro+",
    # Cloud Search
    "1010350001": "Cloud Search",
    # Meet Global Dialing
    "1010360001": "Google Meet Global Dialing",
}

# "Base" product IDs — the main workspace license. Add-ons are everything else.
_BASE_PRODUCT_IDS = {"Google-Apps", "101001", "101005"}


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
    ) -> tuple[dict[str, dict[str, Any]], str]:
        """Fetch all users from Directory API for enrichment.

        Returns:
            Tuple of (dict mapping email → user details, customer_id)
        """
        users: dict[str, dict[str, Any]] = {}
        customer_id = "my_customer"
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
                if customer_id == "my_customer" and user.get("customerId"):
                    customer_id = user["customerId"]

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        logger.warning("Directory API: %d users, customerId=%s", len(users), customer_id)
        return users, customer_id

    async def _fetch_license_assignments(
        self, client: httpx.AsyncClient, token: str, customer_id: str,
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
                        "customerId": customer_id,
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
                        logger.warning(
                            "Licensing API 403 for product %s: %s",
                            product_id, response.text,
                        )
                        break
                    if response.status_code == 404:
                        break
                    if response.status_code != 200:
                        logger.warning("Licensing API error for product %s: %s", product_id, response.status_code)
                        break

                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        logger.warning(
                            "Licensing API product=%s: items=%d, sample=%s",
                            product_id, len(items),
                            items[0] if items else "empty",
                        )
                    for item in items:
                        sku_id = item.get("skuId", "")
                        sku_name = item.get("skuName", "")
                        product_name = item.get("productName", "")
                        resolved_name = (
                            sku_name
                            or GOOGLE_WORKSPACE_SKUS.get(sku_id)
                            or (f"{product_name} ({sku_id})" if product_name else f"Google Workspace ({sku_id})")
                        )
                        assignments.append({
                            "userId": item.get("userId", "").lower(),
                            "skuId": sku_id,
                            "productId": product_id,
                            "license_type": resolved_name,
                        })

                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
            except Exception:
                logger.warning("Failed to query Licensing API for product %s", product_id, exc_info=True)

        logger.warning("Licensing API total assignments: %d", len(assignments))
        return assignments

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all license assignments from Google Workspace.

        Primary source: Licensing API (real license assignments per user/SKU).
        Fallback: Directory API users (all get generic "Google Workspace" type).
        Directory API is always used to enrich with user details.

        Multiple licenses per user are combined into one entry with a combined
        license_type (e.g. "Google Workspace Enterprise Plus + AI Ultra").

        Returns:
            List of license data dicts
        """
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            # Always fetch users for enrichment (name, last login, status)
            users_map, customer_id = await self._fetch_all_users(client, token)

            # Try Licensing API for real license assignments
            assignments = await self._fetch_license_assignments(client, token, customer_id)

            if assignments:
                logger.warning("Using %d license assignments from Licensing API", len(assignments))
                return self._build_from_assignments(assignments, users_map)
            else:
                logger.warning("Licensing API returned no data, falling back to %d Directory API users", len(users_map))
                return self._build_from_users(users_map)

    def _build_from_assignments(
        self,
        assignments: list[dict[str, str]],
        users_map: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build license list from Licensing API assignments enriched with user data.

        Combines multiple license assignments per user into one entry.
        The base license (e.g. Enterprise Plus) comes first, followed by add-ons.
        """
        # Group assignments by user email
        user_assignments: dict[str, list[dict[str, str]]] = defaultdict(list)
        for assignment in assignments:
            user_assignments[assignment["userId"]].append(assignment)

        licenses = []
        for email, user_assgns in user_assignments.items():
            user = users_map.get(email, {})

            # Sort: base licenses first, then add-ons alphabetically
            base = [a for a in user_assgns if a["productId"] in _BASE_PRODUCT_IDS]
            addons = [a for a in user_assgns if a["productId"] not in _BASE_PRODUCT_IDS]
            addons.sort(key=lambda a: a["license_type"])

            ordered = base + addons
            combined_type = " + ".join(a["license_type"] for a in ordered)

            licenses.append(self._build_license_entry(
                email=email,
                license_type=combined_type,
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
