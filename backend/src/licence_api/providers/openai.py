"""OpenAI provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI organization integration for API users."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize OpenAI provider.

        Args:
            credentials: Dict with keys:
                - admin_api_key: OpenAI admin API key
                - org_id: Organization ID
        """
        super().__init__(credentials)
        self.api_key = credentials.get("admin_api_key") or credentials.get("openai_admin_api_key")
        self.org_id = credentials.get("org_id") or credentials.get("openai_org_id")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.org_id:
            headers["OpenAI-Organization"] = self.org_id
        return headers

    async def test_connection(self) -> bool:
        """Test OpenAI API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/organization/users",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all organization members from OpenAI.

        Returns:
            List of license data dicts
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # Fetch organization users
            response = await client.get(
                f"{self.BASE_URL}/organization/users",
                headers=self._get_headers(),
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            for member in data.get("members", data.get("data", [])):
                user = member.get("user", member)

                # Parse added date
                added_at = None
                if member.get("added"):
                    added_at = datetime.fromtimestamp(member["added"])
                elif member.get("created"):
                    added_at = datetime.fromtimestamp(member["created"])

                licenses.append(
                    {
                        "external_user_id": user.get("id", member.get("id")),
                        "email": user.get("email", "").lower(),
                        "license_type": member.get("role", "member"),
                        "status": "active",
                        "assigned_at": added_at,
                        "metadata": {
                            "name": user.get("name"),
                            "role": member.get("role"),
                        },
                    }
                )

        return licenses
