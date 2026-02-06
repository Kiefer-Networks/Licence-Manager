"""Zoom provider integration."""

import base64
import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class ZoomProvider(BaseProvider):
    """Zoom integration for meeting licenses."""

    AUTH_URL = "https://zoom.us/oauth/token"
    API_URL = "https://api.zoom.us/v2"

    # Zoom user types mapping
    USER_TYPES = {
        1: "Basic",
        2: "Licensed",
        3: "On-Prem",
        99: "None",
    }

    # Zoom license types based on plan
    LICENSE_TYPES = {
        1: "Zoom Basic",
        2: "Zoom Pro",
        3: "Zoom Business",
        4: "Zoom Enterprise",
    }

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Zoom provider.

        Args:
            credentials: Dict with keys:
                - account_id: Zoom Account ID
                - client_id: OAuth Client ID
                - client_secret: OAuth Client Secret
        """
        super().__init__(credentials)
        self.account_id = credentials.get("account_id") or credentials.get("zoom_account_id")
        self.client_id = credentials.get("client_id") or credentials.get("zoom_client_id")
        self.client_secret = credentials.get("client_secret") or credentials.get(
            "zoom_client_secret"
        )
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using Server-to-Server OAuth.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        # Create Basic Auth header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.AUTH_URL,
                headers={
                    "Authorization": f"Basic {encoded}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "account_credentials",
                    "account_id": self.account_id,
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.debug("Zoom OAuth error response: %s", response.text)
                raise ValueError("Failed to authenticate with Zoom API")

            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    def _get_headers(self, token: str) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Zoom API connection.

        Returns:
            True if connection is successful
        """
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.API_URL}/users",
                    headers=self._get_headers(token),
                    params={"page_size": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.warning("Zoom connection test failed: %s", e)
            return False

    def _get_license_type(self, user_type: int, plan_type: int | None = None) -> str:
        """Determine license type from user type and plan.

        Args:
            user_type: Zoom user type (1=Basic, 2=Licensed, etc.)
            plan_type: Optional plan type

        Returns:
            License type string
        """
        if user_type == 1:
            return "Zoom Basic"
        elif user_type == 2:
            if plan_type:
                return self.LICENSE_TYPES.get(plan_type, "Zoom Pro")
            return "Zoom Pro"
        elif user_type == 3:
            return "Zoom On-Prem"
        return "Zoom"

    def _get_status(self, status: str) -> str:
        """Map Zoom status to internal status.

        Args:
            status: Zoom user status

        Returns:
            Internal status string
        """
        status_map = {
            "active": "active",
            "inactive": "inactive",
            "pending": "inactive",
        }
        return status_map.get(status.lower(), "active")

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch users/licenses from Zoom.

        Returns:
            List of license data dicts
        """
        licenses = []
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            # Get account info for plan type
            plan_type = None
            try:
                account_response = await client.get(
                    f"{self.API_URL}/accounts/{self.account_id}/plans",
                    headers=self._get_headers(token),
                    timeout=10.0,
                )
                if account_response.status_code == 200:
                    account_data = account_response.json()
                    plan_type = account_data.get("plan_base", {}).get("type")
            except Exception as e:
                logger.debug("Failed to fetch Zoom account plans: %s", e)

            # Fetch all users with pagination
            next_page_token = ""
            page_number = 1

            while True:
                params: dict[str, Any] = {
                    "page_size": 300,
                    "status": "active",
                }
                if next_page_token:
                    params["next_page_token"] = next_page_token

                response = await client.get(
                    f"{self.API_URL}/users",
                    headers=self._get_headers(token),
                    params=params,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.debug("Zoom API error response: %s", response.text)
                    raise ValueError("Failed to fetch users from Zoom API")

                data = response.json()

                for user in data.get("users", []):
                    user_id = user.get("id")
                    email = user.get("email", "").lower().strip()
                    user_type = user.get("type", 1)

                    # Parse timestamps
                    last_login = None
                    if user.get("last_login_time"):
                        try:
                            last_login = datetime.fromisoformat(
                                user["last_login_time"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    created_at = None
                    if user.get("created_at"):
                        try:
                            created_at = datetime.fromisoformat(
                                user["created_at"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    # Determine license type
                    license_type = self._get_license_type(user_type, plan_type)

                    # Determine role
                    role_id = user.get("role_id", 0)
                    if role_id == 0:
                        role = "Owner"
                    elif role_id == 1:
                        role = "Admin"
                    else:
                        role = "Member"

                    # Use email as external_user_id
                    external_id = email if email else user_id

                    licenses.append(
                        {
                            "external_user_id": external_id,
                            "email": email,
                            "license_type": license_type,
                            "status": self._get_status(user.get("status", "active")),
                            "last_activity_at": last_login,
                            "metadata": {
                                "zoom_user_id": user_id,
                                "email": email,
                                "first_name": user.get("first_name"),
                                "last_name": user.get("last_name"),
                                "display_name": (
                                    f"{user.get('first_name', '')} "
                                    f"{user.get('last_name', '')}".strip()
                                ),
                                "user_type": self.USER_TYPES.get(user_type, "Unknown"),
                                "user_type_id": user_type,
                                "role": role,
                                "role_id": role_id,
                                "department": user.get("dept"),
                                "timezone": user.get("timezone"),
                                "created_at": created_at.isoformat() if created_at else None,
                                "pmi": user.get("pmi"),
                                "verified": user.get("verified", 0) == 1,
                            },
                        }
                    )

                # Check for more pages
                next_page_token = data.get("next_page_token", "")
                if not next_page_token:
                    break
                page_number += 1

            # Also fetch inactive/pending users
            for status in ["inactive", "pending"]:
                next_page_token = ""
                while True:
                    params = {
                        "page_size": 300,
                        "status": status,
                    }
                    if next_page_token:
                        params["next_page_token"] = next_page_token

                    response = await client.get(
                        f"{self.API_URL}/users",
                        headers=self._get_headers(token),
                        params=params,
                        timeout=30.0,
                    )

                    if response.status_code != 200:
                        break

                    data = response.json()

                    for user in data.get("users", []):
                        user_id = user.get("id")
                        email = user.get("email", "").lower().strip()
                        user_type = user.get("type", 1)

                        license_type = self._get_license_type(user_type, plan_type)
                        external_id = email if email else user_id

                        licenses.append(
                            {
                                "external_user_id": external_id,
                                "email": email,
                                "license_type": license_type,
                                "status": "inactive",
                                "metadata": {
                                    "zoom_user_id": user_id,
                                    "email": email,
                                    "first_name": user.get("first_name"),
                                    "last_name": user.get("last_name"),
                                    "display_name": (
                                    f"{user.get('first_name', '')} "
                                    f"{user.get('last_name', '')}".strip()
                                ),
                                    "user_type": self.USER_TYPES.get(user_type, "Unknown"),
                                    "original_status": status,
                                },
                            }
                        )

                    next_page_token = data.get("next_page_token", "")
                    if not next_page_token:
                        break

        return licenses
