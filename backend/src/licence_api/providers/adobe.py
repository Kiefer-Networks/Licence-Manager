"""Adobe provider integration for Creative Cloud and Document Cloud."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AdobeProvider(BaseProvider):
    """Adobe Admin Console integration for Creative Cloud/Document Cloud licenses.

    Uses the Adobe User Management API to fetch organization users and their
    product entitlements.
    """

    BASE_URL = "https://usermanagement.adobe.io/v2/usermanagement"
    IMS_URL = "https://ims-na1.adobelogin.com"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Adobe provider.

        Args:
            credentials: Dict with keys:
                - client_id: Adobe API client ID
                - client_secret: Adobe API client secret
                - org_id: Adobe organization ID
                - technical_account_id: Technical account ID (for JWT auth)
                - private_key: Private key for JWT signing (optional, for JWT auth)
        """
        super().__init__(credentials)
        self.client_id = credentials.get("client_id", "")
        self.client_secret = credentials.get("client_secret", "")
        self.org_id = credentials.get("org_id", "")
        self.technical_account_id = credentials.get("technical_account_id", "")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using client credentials.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            # Use OAuth Server-to-Server (client credentials)
            response = await client.post(
                f"{self.IMS_URL}/ims/token/v3",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "openid,AdobeID,user_management_sdk",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error("Failed to get Adobe access token: status=%d", response.status_code)
                raise ValueError(f"Adobe auth failed: {response.status_code}")

            data = response.json()
            self._access_token = data.get("access_token")
            return self._access_token

    def _get_headers(self, access_token: str) -> dict[str, str]:
        """Get API request headers."""
        return {
            "Authorization": f"Bearer {access_token}",
            "x-api-key": self.client_id,
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Adobe API connection.

        Returns:
            True if connection is successful
        """
        try:
            access_token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                # Test by getting organization info
                response = await client.get(
                    f"{self.BASE_URL}/organizations/{self.org_id}/users",
                    headers=self._get_headers(access_token),
                    params={"page": 0, "size": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Adobe connection test failed: %s", e)
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch organization users from Adobe User Management API.

        Returns:
            List of license data dicts
        """
        licenses = []
        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            page = 0
            while True:
                response = await client.get(
                    f"{self.BASE_URL}/organizations/{self.org_id}/users",
                    headers=self._get_headers(access_token),
                    params={"page": page, "size": 100},
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error("Failed to fetch Adobe users: status=%d", response.status_code)
                    raise ValueError(f"Adobe API error: {response.status_code}")

                data = response.json()
                users = data.get("users", [])

                if not users:
                    break

                for user in users:
                    user_id = user.get("id", "")
                    email = user.get("email", "").lower().strip()
                    username = user.get("username", "")
                    first_name = user.get("firstname", "")
                    last_name = user.get("lastname", "")
                    name = f"{first_name} {last_name}".strip() or username

                    # Get user status
                    user_status = user.get("status", "active")
                    if user_status == "active":
                        status = "active"
                    elif user_status == "disabled":
                        status = "inactive"
                    else:
                        status = "suspended"

                    # Get product entitlements (licenses)
                    groups = user.get("groups", [])
                    products = []

                    # Product configurations are in adminRoles or groups
                    for group in groups:
                        if isinstance(group, str):
                            # Filter out admin groups, keep product groups
                            if not group.startswith("_"):
                                products.append(group)
                        elif isinstance(group, dict):
                            group_name = group.get("groupName", "")
                            if group_name and not group_name.startswith("_"):
                                products.append(group_name)

                    # Determine license type from products
                    if products:
                        # Clean up product names
                        clean_products = []
                        for p in products:
                            # Remove common prefixes/suffixes
                            clean_name = p.replace("Default ", "").replace(" - Default Configuration", "")
                            clean_products.append(clean_name)
                        license_type = ", ".join(sorted(set(clean_products)))
                    else:
                        license_type = "Adobe ID Only"

                    # Parse last login timestamp
                    last_activity = None
                    last_login = user.get("lastLogin")
                    if last_login:
                        try:
                            last_activity = datetime.fromisoformat(
                                last_login.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    # Use email as external_user_id if available
                    if email:
                        external_id = email
                    elif name:
                        external_id = f"{name} ({user_id})"
                    else:
                        external_id = user_id

                    # Determine user type
                    user_type = user.get("type", "federatedID")
                    is_federated = user_type == "federatedID"
                    is_enterprise = user_type == "enterpriseID"

                    licenses.append(
                        {
                            "external_user_id": external_id,
                            "email": email,
                            "license_type": license_type,
                            "status": status,
                            "last_activity_at": last_activity,
                            "metadata": {
                                "adobe_user_id": user_id,
                                "email": email,
                                "name": name,
                                "username": username,
                                "user_type": user_type,
                                "is_federated": is_federated,
                                "is_enterprise": is_enterprise,
                                "products": products,
                                "country": user.get("country"),
                                "domain": user.get("domain"),
                            },
                        }
                    )

                # Check if there are more pages
                if len(users) < 100:
                    break
                page += 1

        logger.info("Fetched %d users from Adobe", len(licenses))
        return licenses
