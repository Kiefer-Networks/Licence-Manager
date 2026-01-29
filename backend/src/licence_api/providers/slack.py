"""Slack provider integration."""

from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider


class SlackProvider(BaseProvider):
    """Slack workspace integration for team licenses."""

    BASE_URL = "https://slack.com/api"

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Slack provider.

        Args:
            credentials: Dict with keys:
                - bot_token: Slack bot OAuth token (xoxb-...)
                - user_token: Slack user OAuth token (xoxp-...) for SCIM
        """
        super().__init__(credentials)
        self.bot_token = credentials.get("bot_token") or credentials.get(
            "slack_bot_token"
        )
        self.user_token = credentials.get("user_token") or credentials.get(
            "slack_user_token"
        )

    def _get_headers(self, use_user_token: bool = False) -> dict[str, str]:
        """Get API request headers."""
        token = self.user_token if use_user_token else self.bot_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> bool:
        """Test Slack API connection.

        Returns:
            True if connection is successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/auth.test",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                data = response.json()
                return data.get("ok", False)
        except Exception:
            return False

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch all workspace members from Slack.

        Returns:
            List of license data dicts
        """
        licenses = []
        cursor = None

        async with httpx.AsyncClient() as client:
            while True:
                params: dict[str, Any] = {"limit": 200}
                if cursor:
                    params["cursor"] = cursor

                response = await client.post(
                    f"{self.BASE_URL}/users.list",
                    headers=self._get_headers(),
                    json=params,
                    timeout=30.0,
                )
                data = response.json()

                if not data.get("ok"):
                    raise ValueError(f"Slack API error: {data.get('error')}")

                for member in data.get("members", []):
                    # Skip bots and Slackbot
                    if member.get("is_bot") or member.get("id") == "USLACKBOT":
                        continue

                    # Determine status
                    if member.get("deleted"):
                        status = "suspended"
                    elif member.get("is_restricted") or member.get("is_ultra_restricted"):
                        status = "active"  # Guest accounts are still active
                    else:
                        status = "active"

                    # Determine license type
                    if member.get("is_admin") or member.get("is_owner"):
                        license_type = "Slack Admin"
                    elif member.get("is_ultra_restricted"):
                        license_type = "Slack Single-Channel Guest"
                    elif member.get("is_restricted"):
                        license_type = "Slack Multi-Channel Guest"
                    else:
                        license_type = "Slack Full Member"

                    # Parse updated timestamp as last activity approximation
                    last_activity = None
                    if member.get("updated"):
                        last_activity = datetime.fromtimestamp(member["updated"])

                    profile = member.get("profile", {})

                    licenses.append({
                        "external_user_id": member["id"],
                        "email": profile.get("email", "").lower(),
                        "license_type": license_type,
                        "status": status,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "name": profile.get("real_name") or profile.get("display_name"),
                            "title": profile.get("title"),
                            "is_admin": member.get("is_admin", False),
                            "is_owner": member.get("is_owner", False),
                            "is_guest": member.get("is_restricted", False)
                            or member.get("is_ultra_restricted", False),
                            "tz": member.get("tz"),
                        },
                    })

                # Check for more pages
                cursor = data.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

        return licenses

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Send a message to a Slack channel.

        Args:
            channel: Channel ID or name
            text: Message text (fallback for notifications)
            blocks: Optional Block Kit blocks

        Returns:
            True if message sent successfully
        """
        async with httpx.AsyncClient() as client:
            payload: dict[str, Any] = {
                "channel": channel,
                "text": text,
            }
            if blocks:
                payload["blocks"] = blocks

            response = await client.post(
                f"{self.BASE_URL}/chat.postMessage",
                headers=self._get_headers(),
                json=payload,
                timeout=10.0,
            )
            data = response.json()
            return data.get("ok", False)
