"""1Password provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class OnePasswordProvider(BaseProvider):
    """1Password team member integration via SCIM API."""

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize 1Password provider.

        Args:
            credentials: Dict with keys:
                - api_token: 1Password SCIM bridge token
                - sign_in_address: 1Password sign-in address (e.g., company.1password.com)
        """
        super().__init__(credentials)
        self.api_token = credentials.get("api_token")
        sign_in_address = credentials.get("sign_in_address", "").rstrip("/")
        # SCIM bridge URL format
        if sign_in_address and not sign_in_address.startswith("http"):
            sign_in_address = f"https://{sign_in_address}"
        self.base_url = f"{sign_in_address}/scim/v2" if sign_in_address else ""

    def _get_headers(self) -> dict[str, str]:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/scim+json",
            "Content-Type": "application/scim+json",
        }

    async def test_connection(self) -> bool:
        """Test 1Password SCIM API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/Users",
                    headers=self._get_headers(),
                    params={"count": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users from 1Password via SCIM.

        Returns:
            List of license data dicts
        """
        licenses = []
        start_index = 1
        count = 100

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/Users",
                    headers=self._get_headers(),
                    params={"startIndex": start_index, "count": count},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                resources = data.get("Resources", [])
                if not resources:
                    break

                for user in resources:
                    # Get primary email
                    email = None
                    emails = user.get("emails", [])
                    for e in emails:
                        if e.get("primary"):
                            email = e.get("value")
                            break
                    if not email and emails:
                        email = emails[0].get("value")

                    # Get name
                    name_obj = user.get("name", {})
                    given = name_obj.get("givenName", "")
                    family = name_obj.get("familyName", "")
                    full_name = user.get("displayName") or f"{given} {family}".strip()

                    # Determine status
                    active = user.get("active", True)
                    status = "active" if active else "suspended"

                    # Determine license type based on user type or groups
                    user_type = user.get("userType", "member")
                    license_type = self._get_license_type(user_type)

                    # Parse dates from meta
                    meta = user.get("meta", {})
                    created_at = None
                    if meta.get("created"):
                        created_at = datetime.fromisoformat(meta["created"].replace("Z", "+00:00"))

                    modified_at = None
                    if meta.get("lastModified"):
                        modified_at = datetime.fromisoformat(
                            meta["lastModified"].replace("Z", "+00:00")
                        )

                    # Get groups
                    groups = []
                    for group in user.get("groups", []):
                        groups.append(
                            {
                                "id": group.get("value"),
                                "name": group.get("display"),
                            }
                        )

                    external_id = user.get("externalId") or user.get("id")

                    licenses.append(
                        {
                            "external_user_id": email.lower() if email else external_id,
                            "email": email.lower() if email else None,
                            "license_type": license_type,
                            "status": status,
                            "assigned_at": created_at,
                            "last_activity_at": modified_at,
                            "metadata": {
                                "onepassword_id": user.get("id"),
                                "external_id": user.get("externalId"),
                                "name": full_name,
                                "username": user.get("userName"),
                                "user_type": user_type,
                                "groups": groups,
                                "locale": user.get("locale"),
                                "timezone": user.get("timezone"),
                            },
                        }
                    )

                # Check if there are more results
                total_results = data.get("totalResults", 0)
                items_per_page = data.get("itemsPerPage", count)
                if start_index + items_per_page > total_results:
                    break
                start_index += items_per_page

        return licenses

    def _get_license_type(self, user_type: str) -> str:
        """Convert user type to license type.

        Args:
            user_type: 1Password user type

        Returns:
            License type string
        """
        type_mapping = {
            "owner": "1Password Owner",
            "admin": "1Password Admin",
            "manager": "1Password Manager",
            "member": "1Password Member",
            "guest": "1Password Guest",
        }
        return type_mapping.get(user_type.lower(), f"1Password {user_type.title()}")
