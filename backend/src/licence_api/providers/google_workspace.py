"""Google Workspace provider integration."""

import json
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class GoogleWorkspaceProvider(BaseProvider):
    """Google Workspace integration for user licenses."""

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Google Workspace provider.

        Args:
            credentials: Dict with keys:
                - service_account_json: Service account JSON key (as string)
                - admin_email: Admin email for domain-wide delegation
                - domain: Google Workspace domain
        """
        super().__init__(credentials)
        self.service_account = json.loads(
            credentials.get("service_account_json")
            or credentials.get("google_service_account_json", "{}")
        )
        self.admin_email = credentials.get("admin_email") or credentials.get(
            "google_admin_email"
        )
        self.domain = credentials.get("domain") or credentials.get("google_domain")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using service account.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        import time
        from jose import jwt

        now = int(time.time())
        payload = {
            "iss": self.service_account["client_email"],
            "sub": self.admin_email,
            "scope": "https://www.googleapis.com/auth/admin.directory.user.readonly",
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

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users with licenses from Google Workspace.

        Returns:
            List of license data dicts
        """
        token = await self._get_access_token()
        licenses = []
        page_token = None

        async with httpx.AsyncClient() as client:
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
                        status = "suspended"
                    else:
                        status = "active"

                    # Parse last login time
                    last_activity = None
                    if user.get("lastLoginTime") and user["lastLoginTime"] != "1970-01-01T00:00:00.000Z":
                        last_activity = datetime.fromisoformat(
                            user["lastLoginTime"].replace("Z", "+00:00")
                        )

                    # Parse creation time
                    created_at = None
                    if user.get("creationTime"):
                        created_at = datetime.fromisoformat(
                            user["creationTime"].replace("Z", "+00:00")
                        )

                    licenses.append({
                        "external_user_id": user["id"],
                        "email": user["primaryEmail"].lower(),
                        "license_type": "Google Workspace",
                        "status": status,
                        "assigned_at": created_at,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "name": user.get("name", {}).get("fullName"),
                            "org_unit": user.get("orgUnitPath"),
                            "is_admin": user.get("isAdmin", False),
                        },
                    })

                page_token = data.get("nextPageToken")
                if not page_token:
                    break

        return licenses
