"""Hugging Face provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class HuggingFaceProvider(BaseProvider):
    """Hugging Face Hub provider integration.

    Fetches organization members from Hugging Face Hub API.
    Tracks who has access to your organization's models, datasets, and spaces.

    Credentials required:
        - access_token: Hugging Face access token (from Settings > Access Tokens)
        - organization: Organization name/slug
    """

    BASE_URL = "https://huggingface.co/api"
    PAGE_SIZE = 500

    # Map API roles to license types
    ROLE_LICENSE_MAP = {
        "admin": "Admin",
        "write": "Write",
        "contributor": "Contributor",
        "read": "Read",
    }

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Hugging Face provider."""
        super().__init__(credentials)
        self.access_token = credentials.get("access_token", "")
        self.organization = credentials.get("organization", "")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO 8601 datetime string.

        Args:
            value: Datetime string or None

        Returns:
            Parsed datetime or None
        """
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    async def test_connection(self) -> bool:
        """Test Hugging Face API connection.

        Returns:
            True if connection is successful
        """
        if not self.organization:
            logger.error("Organization name is required")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/organizations/{self.organization}/members",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Hugging Face connection test failed: {e}")
            return False

    async def _fetch_all_members(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch all organization members with pagination.

        Args:
            client: HTTP client instance

        Returns:
            List of member objects
        """
        members = []
        cursor = None

        while True:
            params: dict[str, Any] = {"limit": self.PAGE_SIZE}
            if cursor:
                params["cursor"] = cursor

            response = await client.get(
                f"{self.BASE_URL}/organizations/{self.organization}/members",
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.warning(f"Hugging Face members fetch failed: {response.status_code}")
                break

            data = response.json()

            # Response is a list of members
            if isinstance(data, list):
                members.extend(data)
                # Check for pagination via Link header or response size
                if len(data) < self.PAGE_SIZE:
                    break
                # Get cursor from last item if available
                if data and "_id" in data[-1]:
                    cursor = data[-1]["_id"]
                else:
                    break
            else:
                # Response might be wrapped in a data object
                page_members = data.get("data", data.get("members", []))
                members.extend(page_members)
                if len(page_members) < self.PAGE_SIZE:
                    break
                cursor = data.get("nextCursor")
                if not cursor:
                    break

        return members

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch organization members from Hugging Face.

        Returns:
            List of license data dicts representing members
        """
        licenses = []

        if not self.organization:
            logger.error("Organization name is required")
            return licenses

        async with httpx.AsyncClient() as client:
            try:
                members = await self._fetch_all_members(client)

                for member in members:
                    # Get role - can be at top level or nested
                    role = member.get("role", "read")
                    license_type = self.ROLE_LICENSE_MAP.get(role, "Read")

                    # Get username
                    username = member.get("user", member.get("username", ""))

                    # Build metadata
                    metadata: dict[str, Any] = {
                        "user_id": member.get("_id"),
                        "username": username,
                        "fullname": member.get("fullname"),
                        "role": role,
                        "is_pro": member.get("isPro", False),
                        "two_fa_enabled": member.get("twoFaEnabled", False),
                        "is_external_collaborator": member.get("isExternalCollaborator", False),
                    }

                    # Add resource groups if available
                    resource_groups = member.get("resourceGroups", [])
                    if resource_groups:
                        metadata["resource_groups"] = [
                            {
                                "name": rg.get("name"),
                                "id": rg.get("id"),
                                "role": rg.get("role"),
                            }
                            for rg in resource_groups
                        ]

                    # Get email if available (verified email)
                    email = member.get("verifiedEmail") or member.get("email")
                    user_id = member.get("_id") or username

                    # Use email as external_user_id if available, otherwise fall back to user ID
                    # This allows matching to HRIS employees
                    external_user_id = email if email else user_id

                    # Store original user_id in metadata for reference
                    metadata["hf_user_id"] = user_id

                    licenses.append({
                        "external_user_id": external_user_id,
                        "email": email,
                        "license_type": license_type,
                        "status": "active",
                        "assigned_at": None,  # Not provided in API
                        "last_activity_at": None,  # Not provided in API
                        "metadata": metadata,
                    })

                logger.info(f"Fetched {len(members)} members from Hugging Face")

            except Exception as e:
                logger.error(f"Error fetching Hugging Face members: {e}")

        return licenses

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get Hugging Face organization metadata.

        Returns:
            Dict with organization info or None
        """
        return {
            "provider_type": "ml_platform",
            "organization": self.organization,
        }
