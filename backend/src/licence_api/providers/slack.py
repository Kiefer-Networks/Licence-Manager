"""Slack provider integration."""

import asyncio
import logging
from datetime import datetime
from typing import Any, ClassVar

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)

# Slack API constants
SLACK_API_BASE = "https://slack.com/api"
SLACK_TIMEOUT = 30.0
SLACK_CONNECT_TIMEOUT = 10.0
SLACK_MAX_RETRIES = 3
SLACK_RETRY_DELAY = 1.0

# User-Agent per RFC 7231
USER_AGENT = "LicenseManagementSystem/1.0 (https://github.com/Kiefer-Networks/Licence-Manager)"


class SlackProvider(BaseProvider):
    """Slack workspace integration for team licenses."""

    # Shared HTTP client for connection reuse
    _http_client: ClassVar[httpx.AsyncClient | None] = None

    def __init__(self, credentials: dict[str, Any]) -> None:
        """Initialize Slack provider.

        Args:
            credentials: Dict with keys:
                - bot_token: Slack bot OAuth token (xoxb-...)
                - user_token: Slack user OAuth token (xoxp-...) for SCIM
        """
        super().__init__(credentials)
        self.bot_token = credentials.get("bot_token") or credentials.get("slack_bot_token")
        self.user_token = credentials.get("user_token") or credentials.get("slack_user_token")

    @classmethod
    def _get_http_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client with connection pooling."""
        if cls._http_client is None or cls._http_client.is_closed:
            cls._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(SLACK_TIMEOUT, connect=SLACK_CONNECT_TIMEOUT),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/json",
                },
            )
        return cls._http_client

    @classmethod
    async def close_client(cls) -> None:
        """Close the shared HTTP client."""
        if cls._http_client and not cls._http_client.is_closed:
            await cls._http_client.aclose()
            cls._http_client = None

    def _get_headers(self, use_user_token: bool = False) -> dict[str, str]:
        """Get API request headers with authorization."""
        token = self.user_token if use_user_token else self.bot_token
        return {"Authorization": f"Bearer {token}"}

    async def _api_call_with_retry(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        use_user_token: bool = False,
    ) -> dict[str, Any]:
        """Make Slack API call with retry and rate limit handling.

        Args:
            method: HTTP method (GET or POST)
            endpoint: API endpoint (without base URL)
            json_data: Optional JSON payload
            use_user_token: Use user token instead of bot token

        Returns:
            API response as dict

        Raises:
            ValueError: On non-retryable API errors
            httpx.HTTPError: On connection errors after retries
        """
        client = self._get_http_client()
        url = f"{SLACK_API_BASE}/{endpoint}"
        headers = self._get_headers(use_user_token)

        for attempt in range(SLACK_MAX_RETRIES):
            try:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, json=json_data or {})

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", SLACK_RETRY_DELAY))
                    logger.warning(f"Slack rate limited on {endpoint}, retry in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                data = response.json()

                if data.get("ok"):
                    return data

                error = data.get("error", "unknown_error")

                # Non-retryable errors
                if error in ("invalid_auth", "token_revoked", "account_inactive", "missing_scope"):
                    raise ValueError(f"Slack API error: {error}")

                # Retryable error
                if attempt < SLACK_MAX_RETRIES - 1:
                    delay = SLACK_RETRY_DELAY * (2**attempt)
                    logger.warning(f"Slack API error on {endpoint}: {error}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise ValueError(f"Slack API error after retries: {error}")

            except httpx.TimeoutException:
                if attempt < SLACK_MAX_RETRIES - 1:
                    delay = SLACK_RETRY_DELAY * (2**attempt)
                    logger.warning(f"Slack timeout on {endpoint}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    raise

        return {"ok": False, "error": "max_retries_exceeded"}

    async def test_connection(self) -> bool:
        """Test Slack API connection.

        Returns:
            True if connection is successful
        """
        try:
            data = await self._api_call_with_retry("POST", "auth.test")
            return data.get("ok", False)
        except Exception as e:
            logger.warning("Slack connection test failed: %s", e)
            return False

    async def _fetch_billing_info(self) -> tuple[str, dict[str, Any]]:
        """Fetch workspace plan and billable user info in parallel.

        Returns:
            Tuple of (workspace_plan, billable_info dict)
        """
        workspace_plan = "Slack"
        billable_info: dict[str, Any] = {}

        async def get_plan() -> str:
            """Get workspace plan."""
            try:
                data = await self._api_call_with_retry("GET", "team.billing.info")
                plan = data.get("plan", "").lower()
                plan_map = {
                    "free": "Slack Free",
                    "std": "Slack Pro",
                    "pro": "Slack Pro",
                    "plus": "Slack Business+",
                    "business+": "Slack Business+",
                    "compliance": "Slack Enterprise Grid",
                    "enterprise": "Slack Enterprise Grid",
                }
                return plan_map.get(plan, f"Slack {plan.title()}" if plan else "Slack")
            except Exception as e:
                logger.debug("Failed to fetch Slack billing info: %s", e)
                return "Slack"

        async def get_billable() -> dict[str, Any]:
            """Get billable user info."""
            try:
                data = await self._api_call_with_retry("GET", "team.billableInfo")
                return data.get("billable_info", {})
            except Exception as e:
                logger.debug("Failed to fetch Slack billable info: %s", e)
                return {}

        # Run billing API calls in parallel for speed
        workspace_plan, billable_info = await asyncio.gather(get_plan(), get_billable())
        return workspace_plan, billable_info

    async def fetch_licenses(self) -> list[dict[str, Any]]:
        """Fetch billable workspace members from Slack.

        Uses team.billableInfo API (requires team.billing:read scope) to get
        accurate billing status. Only users with billing_active=true have
        an active (paid) Slack license.

        Uses team.billing.info to get the workspace plan (Pro, Business+, etc.)

        Falls back to users.list only if billing API is not available.

        Returns:
            List of license data dicts
        """
        licenses: list[dict[str, Any]] = []

        # Verify authentication first
        try:
            client = self._get_http_client()
            response = await client.post(
                f"{SLACK_API_BASE}/auth.test",
                headers=self._get_headers(),
            )
            auth_data = response.json()
            if not auth_data.get("ok"):
                logger.warning("Slack auth.test failed: %s", auth_data.get("error"))

            # Check for required OAuth scopes
            scopes = response.headers.get("x-oauth-scopes", "")
            if "users:read.email" not in scopes:
                logger.warning("Missing users:read.email scope - user emails will not be available")
        except Exception as e:
            logger.error("Failed to verify Slack authentication: %s", e)

        # Fetch billing info in parallel
        workspace_plan, billable_info = await self._fetch_billing_info()

        # Fetch all users with pagination
        cursor = None
        while True:
            params: dict[str, Any] = {"limit": 200}
            if cursor:
                params["cursor"] = cursor

            data = await self._api_call_with_retry("POST", "users.list", params)

            for member in data.get("members", []):
                user_id = member.get("id")

                # Skip bots and Slackbot
                if member.get("is_bot") or user_id == "USLACKBOT":
                    continue

                profile = member.get("profile", {})

                # Check billing status - this determines if they have an active license
                user_billing = billable_info.get(user_id, {})
                if billable_info:
                    is_billable = user_billing.get("billing_active", False)
                else:
                    # No billing info - assume active unless deleted or guest
                    is_billable = not (
                        member.get("deleted")
                        or member.get("is_restricted")
                        or member.get("is_ultra_restricted")
                    )

                # Determine status based on billing
                if member.get("deleted"):
                    status = "suspended"
                elif billable_info and not is_billable:
                    status = "inactive"
                else:
                    status = "active"

                # Determine user role for metadata
                if member.get("is_owner"):
                    role = "Owner"
                elif member.get("is_admin"):
                    role = "Admin"
                elif member.get("is_ultra_restricted"):
                    role = "Single-Channel Guest"
                elif member.get("is_restricted"):
                    role = "Multi-Channel Guest"
                else:
                    role = "Member"

                # License type is the workspace plan (same for all users)
                if member.get("is_restricted") or member.get("is_ultra_restricted"):
                    license_type = "Slack Guest"
                else:
                    license_type = workspace_plan

                # Parse updated timestamp as last activity approximation
                last_activity = None
                if member.get("updated"):
                    last_activity = datetime.fromtimestamp(member["updated"])

                email = profile.get("email", "").lower().strip()
                name = profile.get("real_name") or profile.get("display_name") or ""

                # Use email as external_user_id if available
                if email:
                    external_id = email
                elif name:
                    external_id = f"{name} ({user_id})"
                else:
                    external_id = user_id

                licenses.append(
                    {
                        "external_user_id": external_id,
                        "email": email,
                        "license_type": license_type,
                        "status": status,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "slack_user_id": user_id,
                            "email": email,
                            "name": name,
                            "title": profile.get("title"),
                            "role": role,
                            "is_admin": member.get("is_admin", False),
                            "is_owner": member.get("is_owner", False),
                            "is_guest": member.get("is_restricted", False)
                            or member.get("is_ultra_restricted", False),
                            "is_billable": is_billable,
                            "tz": member.get("tz"),
                        },
                    }
                )

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
        payload: dict[str, Any] = {
            "channel": channel,
            "text": text,
        }
        if blocks:
            payload["blocks"] = blocks

        try:
            data = await self._api_call_with_retry("POST", "chat.postMessage", payload)
            return data.get("ok", False)
        except Exception as e:
            logger.error("Failed to send Slack message: %s", e)
            return False
