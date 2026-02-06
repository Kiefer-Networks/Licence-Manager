"""Mailjet email service provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


class MailjetProvider(BaseProvider):
    """Mailjet email service provider integration.

    Fetches sub-accounts and API keys from Mailjet to track email service licenses.
    Mailjet pricing is typically based on email volume, but user/sub-account
    management is important for access control.

    Credentials required:
        - api_key: Mailjet API key (public key)
        - api_secret: Mailjet API secret (private key)
    """

    BASE_URL = "https://api.mailjet.com/v3/REST"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Mailjet provider."""
        super().__init__(credentials)
        self.api_key = credentials.get("api_key", "")
        self.api_secret = credentials.get("api_secret", "")

    def _get_auth(self) -> tuple[str, str]:
        """Get HTTP Basic auth credentials."""
        return (self.api_key, self.api_secret)

    async def test_connection(self) -> bool:
        """Test Mailjet API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                # Test by fetching account info
                response = await client.get(
                    f"{self.BASE_URL}/myprofile",
                    auth=self._get_auth(),
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Mailjet connection test failed: {e}")
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch sub-accounts and API keys from Mailjet.

        Returns:
            List of license data dicts
        """
        licenses = []

        async with httpx.AsyncClient() as client:
            # Fetch API keys (each key represents access)
            try:
                response = await client.get(
                    f"{self.BASE_URL}/apikey",
                    auth=self._get_auth(),
                    params={"Limit": 1000},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    api_keys = data.get("Data", [])

                    for key in api_keys:
                        # Parse dates
                        created_at = None
                        if key.get("CreatedAt"):
                            try:
                                created_at = datetime.fromisoformat(
                                    key["CreatedAt"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        # Determine status
                        status = "active"
                        if key.get("IsActive") is False:
                            status = "inactive"

                        # Determine license type based on key type
                        if key.get("IsMaster"):
                            license_type = "Master Key"
                        else:
                            license_type = "Sub-Account Key"

                        licenses.append(
                            {
                                "external_user_id": key.get("APIKey") or str(key.get("ID")),
                                "email": key.get("ContactEmail"),
                                "license_type": license_type,
                                "status": status,
                                "assigned_at": created_at,
                                "metadata": {
                                    "key_id": key.get("ID"),
                                    "name": key.get("Name"),
                                    "is_master": key.get("IsMaster"),
                                    "runlevel": key.get("Runlevel"),
                                },
                            }
                        )

                    logger.info(f"Fetched {len(api_keys)} API keys from Mailjet")
                else:
                    logger.warning(f"Mailjet API keys fetch failed: {response.status_code}")

            except Exception as e:
                logger.error(f"Error fetching Mailjet API keys: {e}")

            # Fetch users/contacts with access (if available on plan)
            try:
                response = await client.get(
                    f"{self.BASE_URL}/user",
                    auth=self._get_auth(),
                    params={"Limit": 1000},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    users = data.get("Data", [])

                    for user in users:
                        # Check if already added via API key
                        user_email = user.get("Email")
                        if user_email and any(lic.get("email") == user_email for lic in licenses):
                            continue

                        created_at = None
                        if user.get("CreatedAt"):
                            try:
                                created_at = datetime.fromisoformat(
                                    user["CreatedAt"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        last_login = None
                        if user.get("LastLoginAt"):
                            try:
                                last_login = datetime.fromisoformat(
                                    user["LastLoginAt"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        status = "active"
                        if user.get("IsBanned"):
                            status = "banned"

                        licenses.append(
                            {
                                "external_user_id": user_email or str(user.get("ID")),
                                "email": user_email,
                                "license_type": "User Account",
                                "status": status,
                                "assigned_at": created_at,
                                "last_activity_at": last_login,
                                "metadata": {
                                    "user_id": user.get("ID"),
                                    "username": user.get("Username"),
                                    "locale": user.get("Locale"),
                                    "timezone": user.get("Timezone"),
                                },
                            }
                        )

                    logger.info(f"Fetched {len(users)} users from Mailjet")

            except Exception as e:
                logger.debug(f"Mailjet users endpoint not available: {e}")

            # Fetch sender addresses (also represent usage/licenses)
            try:
                response = await client.get(
                    f"{self.BASE_URL}/sender",
                    auth=self._get_auth(),
                    params={"Limit": 1000},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    senders = data.get("Data", [])

                    for sender in senders:
                        sender_email = sender.get("Email")
                        # Only add verified senders as they represent actual usage
                        if not sender.get("Status") == "Active":
                            continue

                        # Check if email already tracked
                        if any(lic.get("email") == sender_email for lic in licenses):
                            continue

                        created_at = None
                        if sender.get("CreatedAt"):
                            try:
                                created_at = datetime.fromisoformat(
                                    sender["CreatedAt"].replace("Z", "+00:00")
                                )
                            except Exception:
                                pass

                        licenses.append(
                            {
                                "external_user_id": f"sender:{sender_email}",
                                "email": sender_email,
                                "license_type": "Verified Sender",
                                "status": "active",
                                "assigned_at": created_at,
                                "metadata": {
                                    "sender_id": sender.get("ID"),
                                    "name": sender.get("Name"),
                                    "is_default": sender.get("IsDefaultSender"),
                                },
                            }
                        )

                    logger.info(f"Processed {len(senders)} senders from Mailjet")

            except Exception as e:
                logger.debug(f"Mailjet senders fetch info: {e}")

        return licenses

    def get_provider_metadata(self) -> dict[str, Any] | None:
        """Get Mailjet account metadata.

        Returns:
            Dict with account info or None
        """
        return {
            "provider_type": "email_service",
            "pricing_model": "volume_based",
        }
