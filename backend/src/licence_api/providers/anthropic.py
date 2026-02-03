"""Anthropic (Claude) provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Anthropic (Claude) API provider integration.

    Fetches organization users and API keys from Anthropic Admin API.
    This helps track who has access to Claude API and their usage.

    Note: Anthropic's Admin API requires organization admin access.

    Credentials required:
        - admin_api_key: Anthropic Admin API key (starts with 'sk-ant-admin-')
    """

    BASE_URL = "https://api.anthropic.com/v1"
    PAGE_SIZE = 100

    # Map API roles to license types
    ROLE_LICENSE_MAP = {
        "admin": "Admin",
        "developer": "Developer",
        "billing": "Billing",
        "user": "User",
        "claude_code_user": "Claude Code User",
    }

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

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse RFC 3339 datetime string.

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
        """Test Anthropic Admin API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/organizations/users",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10.0,
                )
                # 200 = success, 403 = valid key but no admin access
                return response.status_code in [200, 403]
        except Exception as e:
            logger.error(f"Anthropic connection test failed: {e}")
            return False

    async def _fetch_all_users(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch all organization users with pagination.

        Args:
            client: HTTP client instance

        Returns:
            List of user objects
        """
        users = []
        after_id = None

        while True:
            params: dict[str, Any] = {"limit": self.PAGE_SIZE}
            if after_id:
                params["after_id"] = after_id

            response = await client.get(
                f"{self.BASE_URL}/organizations/users",
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )

            if response.status_code != 200:
                if response.status_code == 403:
                    logger.warning("Anthropic Admin API: Forbidden - admin key required")
                else:
                    logger.warning(f"Anthropic users fetch failed: {response.status_code}")
                break

            data = response.json()
            page_users = data.get("data", [])
            users.extend(page_users)

            if not data.get("has_more", False):
                break

            after_id = data.get("last_id")
            if not after_id:
                break

        return users

    async def _fetch_all_api_keys(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch all API keys with pagination.

        Args:
            client: HTTP client instance

        Returns:
            List of API key objects
        """
        api_keys = []
        after_id = None

        while True:
            params: dict[str, Any] = {"limit": self.PAGE_SIZE}
            if after_id:
                params["after_id"] = after_id

            response = await client.get(
                f"{self.BASE_URL}/organizations/api_keys",
                headers=self._get_headers(),
                params=params,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.debug(f"API keys fetch returned {response.status_code}")
                break

            data = response.json()
            page_keys = data.get("data", [])
            api_keys.extend(page_keys)

            if not data.get("has_more", False):
                break

            after_id = data.get("last_id")
            if not after_id:
                break

        return api_keys

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch organization users and API keys from Anthropic.

        Returns:
            List of license data dicts representing users with API access
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # Fetch organization users
            try:
                users = await self._fetch_all_users(client)

                for user in users:
                    role = user.get("role", "user")
                    license_type = self.ROLE_LICENSE_MAP.get(role, "User")

                    licenses.append({
                        "external_user_id": user.get("id"),
                        "email": user.get("email"),
                        "license_type": license_type,
                        "status": "active",
                        "assigned_at": self._parse_datetime(user.get("added_at")),
                        "last_activity_at": None,
                        "metadata": {
                            "user_id": user.get("id"),
                            "name": user.get("name"),
                            "role": role,
                        },
                    })

                logger.info(f"Fetched {len(users)} users from Anthropic")

            except Exception as e:
                logger.error(f"Error fetching Anthropic users: {e}")

            # Fetch API keys
            try:
                api_keys = await self._fetch_all_api_keys(client)

                for key in api_keys:
                    key_id = key.get("id", "")
                    key_name = key.get("name", "API Key")

                    # Check if this key is associated with a user
                    created_by = key.get("created_by", {})
                    owner_id = created_by.get("id") if isinstance(created_by, dict) else None

                    if owner_id:
                        # Update existing license with API key info
                        for lic in licenses:
                            if lic["metadata"].get("user_id") == owner_id:
                                if "api_keys" not in lic["metadata"]:
                                    lic["metadata"]["api_keys"] = []
                                lic["metadata"]["api_keys"].append({
                                    "id": key_id,
                                    "name": key_name,
                                    "status": key.get("status", "active"),
                                })
                                break
                        else:
                            # Owner not in user list, add as separate entry
                            owner_email = created_by.get("email") if isinstance(created_by, dict) else None
                            licenses.append({
                                "external_user_id": f"api_key:{key_id}",
                                "email": owner_email,
                                "license_type": "API Key",
                                "status": "active" if key.get("status") != "disabled" else "disabled",
                                "assigned_at": self._parse_datetime(key.get("created_at")),
                                "last_activity_at": self._parse_datetime(key.get("last_used_at")),
                                "metadata": {
                                    "key_id": key_id,
                                    "key_name": key_name,
                                    "partial_key_hint": key.get("partial_key_hint"),
                                    "workspace_id": key.get("workspace_id"),
                                },
                            })
                    else:
                        # Unassigned/service key
                        licenses.append({
                            "external_user_id": f"api_key:{key_id}",
                            "license_type": "API Key",
                            "status": "active" if key.get("status") != "disabled" else "disabled",
                            "assigned_at": self._parse_datetime(key.get("created_at")),
                            "last_activity_at": self._parse_datetime(key.get("last_used_at")),
                            "metadata": {
                                "key_id": key_id,
                                "key_name": key_name,
                                "partial_key_hint": key.get("partial_key_hint"),
                                "workspace_id": key.get("workspace_id"),
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
