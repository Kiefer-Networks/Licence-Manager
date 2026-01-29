"""Figma provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class FigmaProvider(BaseProvider):
    """Figma organization integration for design licenses."""

    BASE_URL = "https://api.figma.com/v1"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Figma provider.

        Args:
            credentials: Dict with keys:
                - access_token: Figma personal access token or OAuth token
                - org_id: Organization ID (for enterprise)
        """
        super().__init__(credentials)
        self.access_token = credentials.get("access_token") or credentials.get(
            "figma_access_token"
        )
        self.org_id = credentials.get("org_id") or credentials.get("figma_org_id")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "X-Figma-Token": self.access_token,
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Figma API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/me",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all organization members from Figma.

        Returns:
            List of license data dicts
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            if self.org_id:
                # Enterprise: fetch org members
                response = await client.get(
                    f"{self.BASE_URL}/organizations/{self.org_id}/members",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                for member in data.get("members", []):
                    # Determine license type based on role
                    role = member.get("role", "viewer")
                    license_type = "Figma Viewer"
                    if role in ["owner", "admin", "editor"]:
                        license_type = "Figma Professional"

                    licenses.append({
                        "external_user_id": member.get("id"),
                        "email": member.get("email", "").lower(),
                        "license_type": license_type,
                        "status": "active",
                        "metadata": {
                            "name": member.get("handle") or member.get("name"),
                            "role": role,
                        },
                    })
            else:
                # Team-based: fetch team members (fallback)
                # First get teams
                me_response = await client.get(
                    f"{self.BASE_URL}/me",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                me_response.raise_for_status()
                me_data = me_response.json()

                # Add current user
                licenses.append({
                    "external_user_id": me_data.get("id"),
                    "email": me_data.get("email", "").lower(),
                    "license_type": "Figma Professional",
                    "status": "active",
                    "metadata": {
                        "name": me_data.get("handle"),
                    },
                })

        return licenses
