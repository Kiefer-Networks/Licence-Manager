"""Figma provider integration using SCIM API.

Figma's REST API does not provide endpoints for organization/team members.
The SCIM API is the only way to retrieve user information.

Requirements:
- Figma Business or Enterprise plan (SCIM not available on Starter/Professional)
- SCIM token generated from Admin Settings > SCIM Provisioning
- Tenant ID from Admin Settings > SAML SSO

See: https://developers.figma.com/docs/rest-api/scim/
"""

from typing import Any
from urllib.parse import quote, urljoin

import httpx

from licence_api.providers.base import BaseProvider

# Map Figma seat types to license type names
SEAT_TYPE_MAP = {
    "full": "Figma Full Seat",
    "dev": "Figma Dev Mode",
    "collab": "Figma Collaborator",
    "view": "Figma Viewer",
    "viewer": "Figma Viewer",
}


class FigmaProvider(BaseProvider):
    """Figma organization integration using SCIM API.

    Note: Requires Figma Business or Enterprise plan.
    """

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Figma provider.

        Args:
            credentials: Dict with keys:
                - scim_token: SCIM API token from Admin Settings
                - tenant_id: Tenant ID from Admin Settings > SAML SSO
        """
        super().__init__(credentials)
        self.scim_token = credentials.get("scim_token")
        self.tenant_id = credentials.get("tenant_id")
        self.base_url = urljoin(
            "https://www.figma.com/",
            f"scim/v2/{quote(str(self.tenant_id), safe='')}",
        )

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers for SCIM API."""
        return {
            "Authorization": f"Bearer {self.scim_token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Figma SCIM API connection.

        Returns:
            True if connection is successful
        """
        if not self.scim_token or not self.tenant_id:
            return False

        try:
            async with httpx.AsyncClient() as client:
                # Try to fetch users with count=1 to test connection
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
        """Fetch all organization members from Figma via SCIM API.

        Returns:
            List of license data dicts
        """
        licenses = []
        start_index = 1  # SCIM uses 1-based indexing
        page_size = 100

        async with httpx.AsyncClient() as client:
            while True:
                response = await client.get(
                    f"{self.base_url}/Users",
                    headers=self._get_headers(),
                    params={
                        "startIndex": start_index,
                        "count": page_size,
                    },
                    timeout=30.0,
                )
                if response.status_code != 200:
                    error_detail = response.text
                    raise httpx.HTTPStatusError(
                        f"Figma SCIM API error: {response.status_code} - {error_detail}",
                        request=response.request,
                        response=response,
                    )
                data = response.json()

                resources = data.get("Resources", [])
                if not resources:
                    break

                for user in resources:
                    # Extract email from userName or emails array
                    email = user.get("userName", "")
                    if not email:
                        emails = user.get("emails", [])
                        for email_obj in emails:
                            if email_obj.get("primary"):
                                email = email_obj.get("value", "")
                                break
                        if not email and emails:
                            email = emails[0].get("value", "")

                    # Determine seat type from roles array
                    # Note: roles/seatType is only available on Figma Enterprise plans
                    seat_type = None
                    roles = user.get("roles", [])
                    for role in roles:
                        if role.get("type") == "seatType":
                            seat_type = role.get("value", "").lower()
                            break

                    # Map seat type to license type
                    if seat_type:
                        license_type = SEAT_TYPE_MAP.get(seat_type, f"Figma {seat_type.title()}")
                    else:
                        # No seat type available (Business plan) - default to Viewer
                        # Admins can manually adjust license types in the UI
                        license_type = "Figma Viewer"

                    # Build display name
                    display_name = user.get("displayName", "")
                    if not display_name:
                        name_obj = user.get("name", {})
                        given = name_obj.get("givenName", "")
                        family = name_obj.get("familyName", "")
                        display_name = f"{given} {family}".strip()

                    # Extract enterprise extension data
                    enterprise_ext = user.get(
                        "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User", {}
                    )

                    licenses.append(
                        {
                            "external_user_id": user.get("id"),
                            "email": email.lower() if email else "",
                            "license_type": license_type,
                            "status": "active" if user.get("active", True) else "inactive",
                            "metadata": {
                                "name": display_name,
                                "seat_type": seat_type,
                                "figma_admin": user.get("figmaAdmin", False),
                                "department": enterprise_ext.get("department")
                                or user.get("department"),
                                "title": user.get("title"),
                            },
                        }
                    )

                # Check if we've fetched all users
                total_results = data.get("totalResults", 0)
                if start_index + len(resources) > total_results:
                    break

                start_index += page_size

        return licenses
