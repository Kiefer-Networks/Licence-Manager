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
          - For read-only: Token with read permissions
          - For role management: Token with write permissions from an admin user
        - organization: Organization name/slug
        - scim_token: (Optional) SCIM token for fetching user emails (Enterprise only)

    Notes:
        - Without SCIM, only usernames are available - emails require manual linking
        - With SCIM token, user emails can be fetched for automatic matching
        - Member removal is not supported via API (web interface only)
        - Role changes require write permissions on the token
    """

    BASE_URL = "https://huggingface.co/api"
    SCIM_BASE_URL = "https://huggingface.co/api/scim/v2"
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
        self.scim_token = credentials.get("scim_token", "")

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def _get_scim_headers(self) -> dict[str, str]:
        """Get SCIM API request headers."""
        return {
            "Authorization": f"Bearer {self.scim_token}",
            "Content-Type": "application/scim+json",
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

    @property
    def has_email_access(self) -> bool:
        """Check if provider can access user emails.

        Returns True if SCIM token is configured.
        """
        return bool(self.scim_token)

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
                # Hugging Face API requires limit >= 10
                response = await client.get(
                    f"{self.BASE_URL}/organizations/{self.organization}/members",
                    headers=self._get_headers(),
                    params={"limit": 10},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Hugging Face connection test failed: {e}")
            return False

    async def _fetch_scim_users(self, client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
        """Fetch users via SCIM API to get email addresses.

        Args:
            client: HTTP client instance

        Returns:
            Dict mapping username to user info (including email)
        """
        if not self.scim_token:
            return {}

        users = {}
        start_index = 1
        count = 100

        try:
            while True:
                response = await client.get(
                    f"{self.SCIM_BASE_URL}/organizations/{self.organization}/Users",
                    headers=self._get_scim_headers(),
                    params={"startIndex": start_index, "count": count},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.warning(f"SCIM users fetch failed: {response.status_code}")
                    break

                data = response.json()
                resources = data.get("Resources", [])

                for user in resources:
                    username = user.get("userName", "")
                    emails = user.get("emails", [])
                    primary_email = None
                    for email in emails:
                        if email.get("primary"):
                            primary_email = email.get("value")
                            break
                    if not primary_email and emails:
                        primary_email = emails[0].get("value")

                    if username:
                        users[username] = {
                            "email": primary_email,
                            "display_name": user.get("displayName"),
                            "active": user.get("active", True),
                        }

                total_results = data.get("totalResults", 0)
                if start_index + len(resources) > total_results:
                    break
                start_index += count

            logger.info(f"Fetched {len(users)} users via SCIM")

        except Exception as e:
            logger.warning(f"SCIM fetch failed, falling back to standard API: {e}")

        return users

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
                # First try to fetch SCIM users for email addresses
                scim_users = await self._fetch_scim_users(client)

                # Then fetch members from standard API
                members = await self._fetch_all_members(client)

                members_with_email = 0
                members_without_email = 0

                for member in members:
                    # Get role - can be at top level or nested
                    role = member.get("role", "read")
                    license_type = self.ROLE_LICENSE_MAP.get(role, "Read")

                    # Get username
                    username = member.get("user", member.get("username", ""))

                    # Try to get email from SCIM data first, then from member data
                    email = None
                    scim_user = scim_users.get(username, {})
                    if scim_user:
                        email = scim_user.get("email")

                    if not email:
                        email = member.get("verifiedEmail") or member.get("email")

                    if email:
                        members_with_email += 1
                    else:
                        members_without_email += 1

                    # Build metadata
                    metadata: dict[str, Any] = {
                        "user_id": member.get("_id"),
                        "username": username,
                        "fullname": member.get("fullname"),
                        "role": role,
                        "is_pro": member.get("isPro", False),
                        "two_fa_enabled": member.get("twoFaEnabled", False),
                        "is_external_collaborator": member.get("isExternalCollaborator", False),
                        "has_email": bool(email),
                        "requires_manual_linking": not bool(email),
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

                    user_id = member.get("_id") or username

                    # Use email as external_user_id if available, otherwise use username
                    # This allows matching via email or manual username linking
                    external_user_id = email if email else username

                    # Store original user_id and username in metadata for reference
                    metadata["hf_user_id"] = user_id
                    metadata["hf_username"] = username

                    licenses.append({
                        "external_user_id": external_user_id,
                        "email": email,
                        "license_type": license_type,
                        "status": "active",
                        "assigned_at": None,  # Not provided in API
                        "last_activity_at": None,  # Not provided in API
                        "metadata": metadata,
                    })

                logger.info(
                    f"Fetched {len(members)} members from Hugging Face "
                    f"({members_with_email} with email, {members_without_email} require manual linking)"
                )

            except Exception as e:
                logger.error(f"Error fetching Hugging Face members: {e}")

        return licenses

    async def change_member_role(
        self, username: str, role: str, resource_groups: list[dict[str, str]] | None = None
    ) -> bool:
        """Change a member's role in the organization.

        Args:
            username: Hugging Face username of the member
            role: New role (admin, write, contributor, read)
            resource_groups: Optional list of resource group assignments
                             [{"id": "group-id", "role": "write"}, ...]

        Returns:
            True if role change was successful
        """
        if not self.organization:
            logger.error("Organization name is required")
            return False

        if role not in self.ROLE_LICENSE_MAP:
            logger.error(f"Invalid role: {role}. Must be one of: {list(self.ROLE_LICENSE_MAP.keys())}")
            return False

        try:
            async with httpx.AsyncClient() as client:
                payload: dict[str, Any] = {"role": role}
                if resource_groups:
                    payload["resourceGroups"] = resource_groups

                response = await client.put(
                    f"{self.BASE_URL}/organizations/{self.organization}/members/{username}/role",
                    headers=self._get_headers(),
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code == 200:
                    logger.info(f"Changed role for {username} to {role}")
                    return True
                else:
                    logger.error(
                        f"Failed to change role for {username}: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Error changing member role: {e}")
            return False

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get Hugging Face organization metadata.

        Returns:
            Dict with organization info or None
        """
        return {
            "provider_type": "ml_platform",
            "organization": self.organization,
            "supports_role_change": True,
            "supports_member_removal": False,
            "has_email_access": self.has_email_access,
            "requires_manual_linking": not self.has_email_access,
            "manual_linking_hint": (
                "This provider returns usernames only. "
                "Use manual linking to associate members with employees."
            ) if not self.has_email_access else None,
        }
