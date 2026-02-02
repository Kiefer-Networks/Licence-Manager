"""JetBrains provider integration."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class JetBrainsProvider(BaseProvider):
    """JetBrains license management integration.

    API: https://account.jetbrains.com/openapi
    Auth: API Key (X-Api-Key header) + Customer Code (X-Customer-Code header)
    """

    BASE_URL = "https://account.jetbrains.com/api/v1"

    # Product code to friendly name mapping
    PRODUCT_NAMES = {
        "II": "IntelliJ IDEA Ultimate",
        "IIC": "IntelliJ IDEA Community",
        "PS": "PhpStorm",
        "WS": "WebStorm",
        "PY": "PyCharm Professional",
        "PCC": "PyCharm Community",
        "RM": "RubyMine",
        "CL": "CLion",
        "GO": "GoLand",
        "RD": "Rider",
        "DS": "DataSpell",
        "DG": "DataGrip",
        "AC": "AppCode",
        "FL": "Fleet",
        "RR": "RustRover",
        "QA": "Aqua",
        "AIE": "AI Assistant Enterprise",
        "ALL": "All Products Pack",
    }

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize JetBrains provider.

        Args:
            credentials: Dict with keys:
                - api_key: JetBrains API key
                - customer_code: Customer/organization code
        """
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.customer_code = credentials.get("customer_code", "")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "X-Api-Key": self.api_key,
            "X-Customer-Code": self.customer_code,
            "Accept": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test JetBrains API connection.

        Returns:
            True if connection is successful

        Raises:
            ValueError: If credentials are invalid
        """
        if not self.api_key:
            raise ValueError("API key is required")
        if not self.customer_code:
            raise ValueError("Customer code is required")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/token",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return True
                elif response.status_code == 401:
                    raise ValueError("Invalid API key")
                elif response.status_code == 403:
                    raise ValueError("Access forbidden - check API key permissions")
                else:
                    raise ValueError(f"API error: {response.status_code}")
        except httpx.RequestError as e:
            raise ValueError(f"Connection error: {str(e)}")

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all licenses from JetBrains.

        Returns:
            List of license data dicts
        """
        if not self.api_key or not self.customer_code:
            return []

        licenses = []
        page = 1
        per_page = 100

        try:
            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        f"{self.BASE_URL}/customer/licenses",
                        headers=self._get_headers(),
                        params={"page": page, "perPage": per_page},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if not data:
                        break

                    for lic in data:
                        license_id = lic.get("licenseId", "")
                        product = lic.get("product", {})
                        product_code = product.get("code", "")
                        product_name = product.get("name") or self.PRODUCT_NAMES.get(
                            product_code, product_code
                        )

                        assignee = lic.get("assignee")
                        team = lic.get("team", {})
                        is_suspended = lic.get("isSuspended", False)
                        is_trial = lic.get("isTrial", False)

                        # Determine assignee info
                        email = None
                        assignee_name = None
                        assignee_type = None

                        if assignee:
                            assignee_type = assignee.get("type")
                            if assignee_type == "USER":
                                email = assignee.get("email", "").lower()
                                assignee_name = assignee.get("name")
                            elif assignee_type == "SERVER":
                                email = f"server:{assignee.get('uid', 'unknown')}"
                                assignee_name = f"License Server ({assignee.get('serverType', 'UNKNOWN')})"
                            elif assignee_type == "LICENSE_KEY":
                                email = f"key:{license_id}"
                                assignee_name = assignee.get("registrationName", "License Key")

                        # Determine status
                        # Note: "unassigned" should be determined by employee_id at the system level,
                        # not by provider status. All non-suspended licenses are "active".
                        if is_suspended:
                            status = "inactive"
                        else:
                            status = "active"

                        # Get last activity from lastSeen
                        last_seen = lic.get("lastSeen", {})
                        last_activity = None
                        if last_seen.get("lastSeenDate"):
                            try:
                                last_activity = datetime.fromisoformat(
                                    last_seen["lastSeenDate"].replace("Z", "+00:00")
                                )
                            except (ValueError, TypeError):
                                pass

                        # Get subscription info
                        subscription = lic.get("subscription", {})
                        perpetual = lic.get("perpetual", {})
                        valid_until = None
                        is_renewed = False

                        if subscription:
                            if subscription.get("validUntilDate"):
                                try:
                                    valid_until = datetime.fromisoformat(
                                        subscription["validUntilDate"].replace("Z", "+00:00")
                                    )
                                except (ValueError, TypeError):
                                    pass
                            is_renewed = subscription.get("isAutomaticallyRenewed", False)

                        # License type
                        license_type = product_name
                        if is_trial:
                            license_type = f"{product_name} (Trial)"

                        licenses.append({
                            "external_user_id": license_id,
                            "email": email,
                            "license_type": license_type,
                            "status": status,
                            "monthly_cost": None,  # JetBrains is yearly, cost set at org level
                            "currency": "USD",
                            "last_activity_at": last_activity,
                            "metadata": {
                                "license_id": license_id,
                                "product_code": product_code,
                                "email": email,  # Store email for display
                                "assignee_name": assignee_name,
                                "assignee_type": assignee_type,
                                "team_id": team.get("id"),
                                "team_name": team.get("name"),
                                "is_trial": is_trial,
                                "is_suspended": is_suspended,
                                "valid_until": valid_until.isoformat() if valid_until else None,
                                "is_auto_renewed": is_renewed,
                            },
                        })

                    # Check if there are more pages
                    if len(data) < per_page:
                        break
                    page += 1

        except Exception:
            pass

        return licenses
