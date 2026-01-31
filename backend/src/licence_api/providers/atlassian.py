"""Atlassian provider integration for Confluence/Jira Cloud."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class AtlassianProvider(BaseProvider):
    """Atlassian Cloud integration for Confluence/Jira licenses.

    Uses the Atlassian Admin API to fetch organization users.
    Requires an API token with organization admin access.
    """

    ADMIN_API_BASE = "https://api.atlassian.com"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Atlassian provider.

        Args:
            credentials: Dict with keys:
                - api_token: Atlassian API token
                - org_id: Atlassian organization ID
                - admin_email: Admin user email for authentication
        """
        super().__init__(credentials)
        self.api_token = credentials.get("api_token", "")
        self.org_id = credentials.get("org_id", "")
        self.admin_email = credentials.get("admin_email", "")

    def _get_basic_auth(self) -> httpx.BasicAuth:
        """Get httpx BasicAuth for Jira/Confluence REST API.

        Uses httpx.BasicAuth for secure credential handling.
        """
        return httpx.BasicAuth(self.admin_email, self.api_token)

    def _get_headers(self) -> dict[str, str]:
        """Get API request headers for requests using BasicAuth.

        Note: Use _get_basic_auth() with httpx client auth parameter.
        """
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_bearer_headers(self) -> dict[str, str]:
        """Get API request headers with Bearer token for Admin API."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Atlassian API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Test Admin API access
                response = await client.get(
                    f"{self.ADMIN_API_BASE}/admin/v1/orgs/{self.org_id}",
                    headers=self._get_bearer_headers(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error("Atlassian connection test failed: %s", e)
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch organization users from Atlassian Admin API.

        Returns:
            List of license data dicts
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # First, get organization info
            try:
                org_response = await client.get(
                    f"{self.ADMIN_API_BASE}/admin/v1/orgs/{self.org_id}",
                    headers=self._get_bearer_headers(),
                    timeout=30.0,
                )
                if org_response.status_code != 200:
                    logger.error(
                        "Failed to get organization info: status=%d",
                        org_response.status_code,
                    )
                    raise ValueError(f"Atlassian API error: {org_response.status_code}")
            except httpx.HTTPError as e:
                logger.error("HTTP error fetching organization: %s", e)
                raise

            # Fetch users with pagination
            cursor = None
            while True:
                url = f"{self.ADMIN_API_BASE}/admin/v1/orgs/{self.org_id}/users"
                params: dict[str, Any] = {"maxResults": 100}
                if cursor:
                    params["cursor"] = cursor

                response = await client.get(
                    url,
                    headers=self._get_bearer_headers(),
                    params=params,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    logger.error("Failed to fetch users: status=%d", response.status_code)
                    raise ValueError(f"Atlassian API error: {response.status_code}")

                data = response.json()

                for user in data.get("data", []):
                    account_id = user.get("account_id", "")
                    email = user.get("email", "").lower().strip()
                    name = user.get("name", "")
                    account_type = user.get("account_type", "atlassian")
                    account_status = user.get("account_status", "active")

                    # Skip app/bot accounts
                    if account_type == "app":
                        continue

                    # Determine status
                    if account_status == "inactive":
                        status = "inactive"
                    elif account_status == "closed":
                        status = "suspended"
                    else:
                        status = "active"

                    # Get product access info
                    product_access = user.get("product_access", [])
                    products = []
                    for access in product_access:
                        product_name = access.get("name", "")
                        if product_name:
                            products.append(product_name)

                    # License type based on products
                    if products:
                        license_type = ", ".join(sorted(set(products)))
                    else:
                        license_type = "Atlassian Cloud"

                    # Parse last active timestamp
                    last_activity = None
                    last_active = user.get("last_active")
                    if last_active:
                        try:
                            last_activity = datetime.fromisoformat(
                                last_active.replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    # Use email as external_user_id if available
                    if email:
                        external_id = email
                    elif name:
                        external_id = f"{name} ({account_id})"
                    else:
                        external_id = account_id

                    licenses.append(
                        {
                            "external_user_id": external_id,
                            "email": email,
                            "license_type": license_type,
                            "status": status,
                            "last_activity_at": last_activity,
                            "metadata": {
                                "atlassian_account_id": account_id,
                                "email": email,
                                "name": name,
                                "account_type": account_type,
                                "account_status": account_status,
                                "products": products,
                            },
                        }
                    )

                # Check for more pages
                links = data.get("links", {})
                next_link = links.get("next")
                if next_link:
                    # Extract cursor from next link
                    import urllib.parse

                    parsed = urllib.parse.urlparse(next_link)
                    query_params = urllib.parse.parse_qs(parsed.query)
                    cursor = query_params.get("cursor", [None])[0]
                else:
                    break

        logger.info("Fetched %d users from Atlassian", len(licenses))
        return licenses

    async def fetch_product_licenses(self) -> dict[str, Any]:
        """Fetch product license information.

        Returns:
            Dict with product license counts and details
        """
        products = {}

        async with httpx.AsyncClient() as client:
            # Get managed products
            response = await client.get(
                f"{self.ADMIN_API_BASE}/admin/v1/orgs/{self.org_id}/products",
                headers=self._get_bearer_headers(),
                timeout=30.0,
            )

            if response.status_code == 200:
                data = response.json()
                for product in data.get("data", []):
                    product_key = product.get("key", "")
                    product_name = product.get("name", product_key)
                    products[product_key] = {
                        "name": product_name,
                        "url": product.get("url"),
                    }

        return products
