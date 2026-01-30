"""Microsoft 365 / Azure AD provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class MicrosoftProvider(BaseProvider):
    """Microsoft 365 / Azure AD integration for user licenses."""

    GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
    LOGIN_URL = "https://login.microsoftonline.com"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Microsoft provider.

        Args:
            credentials: Dict with keys:
                - tenant_id: Azure AD tenant ID
                - client_id: Application (client) ID
                - client_secret: Client secret
        """
        super().__init__(credentials)
        self.tenant_id = credentials.get("tenant_id")
        self.client_id = credentials.get("client_id")
        self.client_secret = credentials.get("client_secret")
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        """Get OAuth access token using client credentials flow.

        Returns:
            Access token string
        """
        if self._access_token:
            return self._access_token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.LOGIN_URL}/{self.tenant_id}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def test_connection(self) -> bool:
        """Test Microsoft Graph API connection.

        Returns:
            True if connection is successful
        """
        try:
            token = await self._get_access_token()
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.GRAPH_BASE_URL}/users",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"$top": 1},
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _get_sku_mapping(self, token: str) -> dict[str, str]:
        """Fetch SKU ID to product name mapping.

        Args:
            token: Access token

        Returns:
            Dict mapping SKU ID to product display name
        """
        sku_map = {}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GRAPH_BASE_URL}/subscribedSkus",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                for sku in data.get("value", []):
                    sku_id = sku.get("skuId")
                    sku_name = sku.get("skuPartNumber", "Unknown")
                    # Map common SKU part numbers to friendly names
                    friendly_name = self._get_friendly_sku_name(sku_name)
                    sku_map[sku_id] = friendly_name
        return sku_map

    def _get_friendly_sku_name(self, sku_part_number: str) -> str:
        """Convert SKU part number to friendly name.

        Args:
            sku_part_number: Microsoft SKU part number

        Returns:
            Human-readable product name
        """
        # Common Microsoft 365 SKU mappings
        sku_names = {
            "ENTERPRISEPACK": "Microsoft 365 E3",
            "ENTERPRISEPREMIUM": "Microsoft 365 E5",
            "SPE_E3": "Microsoft 365 E3",
            "SPE_E5": "Microsoft 365 E5",
            "SPE_F1": "Microsoft 365 F3",
            "STANDARDPACK": "Microsoft 365 E1",
            "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
            "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
            "SMB_BUSINESS_PREMIUM": "Microsoft 365 Business Premium",
            "EXCHANGESTANDARD": "Exchange Online (Plan 1)",
            "EXCHANGEENTERPRISE": "Exchange Online (Plan 2)",
            "POWER_BI_STANDARD": "Power BI (free)",
            "POWER_BI_PRO": "Power BI Pro",
            "PROJECTPROFESSIONAL": "Project Plan 3",
            "VISIOCLIENT": "Visio Plan 2",
            "TEAMS_EXPLORATORY": "Teams Exploratory",
            "FLOW_FREE": "Power Automate Free",
            "POWERAPPS_VIRAL": "Power Apps Plan 2 Trial",
            "AAD_PREMIUM": "Azure AD Premium P1",
            "AAD_PREMIUM_P2": "Azure AD Premium P2",
            "EMS": "Enterprise Mobility + Security E3",
            "EMSPREMIUM": "Enterprise Mobility + Security E5",
            "DEFENDER_ENDPOINT_P1": "Microsoft Defender for Endpoint P1",
            "WIN_DEF_ATP": "Microsoft Defender for Endpoint P2",
            "INTUNE_A": "Microsoft Intune",
        }
        return sku_names.get(sku_part_number, sku_part_number)

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all users with licenses from Microsoft 365.

        Returns:
            List of license data dicts
        """
        token = await self._get_access_token()

        # Get SKU mapping for friendly license names
        sku_map = await self._get_sku_mapping(token)

        licenses = []
        next_link = f"{self.GRAPH_BASE_URL}/users"

        # Select fields we need, include license assignments
        params: dict[str, Any] = {
            "$select": "id,userPrincipalName,displayName,accountEnabled,createdDateTime,signInActivity,assignedLicenses,department,jobTitle",
            "$top": 999,
        }

        async with httpx.AsyncClient() as client:
            while next_link:
                response = await client.get(
                    next_link,
                    headers={"Authorization": f"Bearer {token}"},
                    params=params if "?" not in next_link else None,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                for user in data.get("value", []):
                    assigned_licenses = user.get("assignedLicenses", [])

                    # Skip users without licenses
                    if not assigned_licenses:
                        continue

                    # Determine status
                    if user.get("accountEnabled"):
                        status = "active"
                    else:
                        status = "suspended"

                    # Parse sign-in activity
                    last_activity = None
                    sign_in = user.get("signInActivity", {})
                    if sign_in:
                        last_sign_in = sign_in.get("lastSignInDateTime")
                        if last_sign_in:
                            last_activity = datetime.fromisoformat(
                                last_sign_in.replace("Z", "+00:00")
                            )

                    # Parse creation time
                    created_at = None
                    if user.get("createdDateTime"):
                        created_at = datetime.fromisoformat(
                            user["createdDateTime"].replace("Z", "+00:00")
                        )

                    # Get license names
                    license_names = []
                    for lic in assigned_licenses:
                        sku_id = lic.get("skuId")
                        if sku_id and sku_id in sku_map:
                            license_names.append(sku_map[sku_id])
                        elif sku_id:
                            license_names.append(sku_id)

                    # Sort license names alphabetically for consistent grouping
                    # This ensures "A, B, C" and "C, B, A" are stored the same way
                    license_names.sort()

                    # User principal name is the email
                    email = user.get("userPrincipalName", "").lower()

                    licenses.append({
                        "external_user_id": email,  # Use email as external ID for matching
                        "email": email,
                        "license_type": ", ".join(license_names) if license_names else "Microsoft 365",
                        "status": status,
                        "assigned_at": created_at,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "azure_id": user.get("id"),
                            "name": user.get("displayName"),
                            "department": user.get("department"),
                            "job_title": user.get("jobTitle"),
                            "license_skus": [lic.get("skuId") for lic in assigned_licenses],
                        },
                    })

                # Handle pagination
                next_link = data.get("@odata.nextLink")
                params = {}  # Clear params for subsequent requests

        return licenses
