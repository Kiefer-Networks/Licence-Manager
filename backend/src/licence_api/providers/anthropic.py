"""Anthropic (Claude) provider integration."""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) API provider integration.

    Fetches organization members and API key usage from Anthropic Admin API.
    This helps track who has access to Claude API and their usage.

    Note: Anthropic's Admin API requires organization admin access.
    The API is relatively new and may have limited endpoints.

    Credentials required:
        - admin_api_key: Anthropic Admin API key (starts with 'sk-ant-admin-')
    """

    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Anthropic provider."""
        super().__init__(credentials)
        self.admin_api_key = credentials.get("admin_api_key", "")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "x-api-key": self.admin_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Anthropic Admin API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Try to fetch organization members
                response = await client.get(
                    f"{self.BASE_URL}/organizations/members",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                # 200 = success, 403 = valid key but no admin access
                return response.status_code in [200, 403]
        except Exception as e:
            logger.error(f"Anthropic connection test failed: {e}")
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch organization members and API keys from Anthropic.

        Returns:
            List of license data dicts representing members with API access
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # Fetch organization members
            try:
                response = await client.get(
                    f"{self.BASE_URL}/organizations/members",
                    headers=self._get_headers(),
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    members = data.get("members", data.get("data", []))

                    for member in members:
                        # Parse dates
                        created_at = None
                        if member.get("created_at"):
                            try:
                                created_at = datetime.fromisoformat(
                                    member["created_at"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        last_active = None
                        if member.get("last_active_at"):
                            try:
                                last_active = datetime.fromisoformat(
                                    member["last_active_at"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        # Determine license type based on role
                        role = member.get("role", "member")
                        if role == "admin":
                            license_type = "Admin"
                        elif role == "developer":
                            license_type = "Developer"
                        else:
                            license_type = "Member"

                        status = "active"
                        if member.get("status") == "disabled":
                            status = "disabled"
                        elif member.get("status") == "pending":
                            status = "pending"

                        licenses.append({
                            "external_user_id": member.get("email") or member.get("id"),
                            "email": member.get("email"),
                            "license_type": license_type,
                            "status": status,
                            "assigned_at": created_at,
                            "last_activity_at": last_active,
                            "metadata": {
                                "member_id": member.get("id"),
                                "name": member.get("name"),
                                "role": role,
                            },
                        })

                    logger.info(f"Fetched {len(licenses)} members from Anthropic")

                elif response.status_code == 403:
                    logger.warning("Anthropic Admin API: Forbidden - may need admin key")
                else:
                    logger.warning(f"Anthropic members fetch failed: {response.status_code}")

            except Exception as e:
                logger.error(f"Error fetching Anthropic members: {e}")

            # Also try to fetch API keys (if available)
            try:
                response = await client.get(
                    f"{self.BASE_URL}/organizations/api_keys",
                    headers=self._get_headers(),
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    api_keys = data.get("api_keys", data.get("data", []))

                    for key in api_keys:
                        # Only add if not already tracked by member
                        key_name = key.get("name", "API Key")
                        key_id = key.get("id", "")

                        # Check if this key is already associated with a member
                        owner_email = key.get("created_by", {}).get("email")
                        if owner_email and any(l["email"] == owner_email for l in licenses):
                            # Update existing license with API key info
                            for lic in licenses:
                                if lic["email"] == owner_email:
                                    if "api_keys" not in lic["metadata"]:
                                        lic["metadata"]["api_keys"] = []
                                    lic["metadata"]["api_keys"].append({
                                        "id": key_id,
                                        "name": key_name,
                                    })
                            continue

                        # Add as separate license entry for unassigned/service keys
                        created_at = None
                        if key.get("created_at"):
                            try:
                                created_at = datetime.fromisoformat(
                                    key["created_at"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        last_used = None
                        if key.get("last_used_at"):
                            try:
                                last_used = datetime.fromisoformat(
                                    key["last_used_at"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        licenses.append({
                            "external_user_id": f"api_key:{key_id}",
                            "license_type": "API Key",
                            "status": "active" if key.get("status") != "disabled" else "disabled",
                            "assigned_at": created_at,
                            "last_activity_at": last_used,
                            "metadata": {
                                "key_id": key_id,
                                "key_name": key_name,
                                "key_prefix": key.get("key_prefix"),
                            },
                        })

                    logger.info(f"Processed {len(api_keys)} API keys from Anthropic")

            except Exception as e:
                logger.debug(f"API keys endpoint not available or error: {e}")

        return licenses

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get Anthropic organization metadata.

        Returns:
            Dict with organization info or None
        """
        return {
            "provider_type": "ai_api",
            "pricing_model": "usage_based",
        }
