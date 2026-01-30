"""Slack provider integration."""

import logging
from datetime import datetime
from typing import Any

import httpx

from licence_api.providers.base import BaseProvider

logger = logging.getLogger(__name__)


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
        """Fetch billable workspace members from Slack.

        Uses team.billableInfo API (requires team.billing:read scope) to get
        accurate billing status. Only users with billing_active=true have
        an active (paid) Slack license.

        Uses team.billing.info to get the workspace plan (Pro, Business+, etc.)

        Falls back to users.list only if billing API is not available.

        Returns:
            List of license data dicts
        """
        licenses = []
        billable_info = {}
        workspace_plan = "Slack"  # Default if we can't get plan info

        async with httpx.AsyncClient() as client:
            # DEBUG: Check auth and scopes
            try:
                auth_response = await client.post(
                    f"{self.BASE_URL}/auth.test",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                auth_data = auth_response.json()
                logger.info(f"[SLACK DEBUG] Auth test response: {auth_data}")

                # Check OAuth scopes (returned in headers)
                scopes = auth_response.headers.get("x-oauth-scopes", "")
                logger.info(f"[SLACK DEBUG] Bot token scopes: {scopes}")
                if "users:read.email" not in scopes:
                    logger.warning("[SLACK DEBUG] MISSING SCOPE: users:read.email - emails will not be returned!")
            except Exception as e:
                logger.error(f"[SLACK DEBUG] Auth test failed: {e}")
            # Get workspace plan info
            try:
                plan_response = await client.get(
                    f"{self.BASE_URL}/team.billing.info",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                plan_data = plan_response.json()

                if plan_data.get("ok"):
                    # Plan names from API: free, std, plus, compliance, enterprise
                    # std = Pro, plus = Business+, compliance = Enterprise Grid
                    plan = plan_data.get("plan", "").lower()
                    plan_map = {
                        "free": "Slack Free",
                        "std": "Slack Pro",
                        "pro": "Slack Pro",
                        "plus": "Slack Business+",
                        "business+": "Slack Business+",
                        "compliance": "Slack Enterprise Grid",
                        "enterprise": "Slack Enterprise Grid",
                    }
                    workspace_plan = plan_map.get(plan, f"Slack {plan.title()}" if plan else "Slack")
            except Exception:
                # Plan API failed - use default
                pass

            # Get billing info to know who actually has a paid license
            try:
                billing_response = await client.get(
                    f"{self.BASE_URL}/team.billableInfo",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
                billing_data = billing_response.json()

                if billing_data.get("ok"):
                    billable_info = billing_data.get("billable_info", {})
            except Exception:
                # Billing API failed - continue without it
                pass

            # Now get user details for all users
            cursor = None
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

                # DEBUG: Log first 3 members raw to see full API structure
                if not cursor:  # Only on first page
                    sample_members = data.get("members", [])[:3]
                    for i, sample in enumerate(sample_members):
                        logger.info(f"[SLACK DEBUG] Sample member {i+1} RAW: {sample}")

                for member in data.get("members", []):
                    user_id = member.get("id")

                    # Skip bots and Slackbot
                    if member.get("is_bot") or user_id == "USLACKBOT":
                        logger.debug(f"[SLACK DEBUG] Skipping bot: {user_id}")
                        continue

                    # DEBUG: Log full member data for users without email
                    profile = member.get("profile", {})
                    member_email = profile.get("email", "")
                    if not member_email:
                        logger.warning(
                            f"[SLACK DEBUG] User WITHOUT email - ID: {user_id}\n"
                            f"  Full profile keys: {list(profile.keys())}\n"
                            f"  Profile: {profile}\n"
                            f"  deleted={member.get('deleted')}, "
                            f"is_restricted={member.get('is_restricted')}, "
                            f"is_ultra_restricted={member.get('is_ultra_restricted')}"
                        )
                    else:
                        logger.info(f"[SLACK DEBUG] User WITH email: {user_id} -> {member_email}")

                    # Check billing status - this determines if they have an active license
                    user_billing = billable_info.get(user_id, {})
                    # If billing info is available, use it; otherwise assume active for non-deleted users
                    if billable_info:
                        is_billable = user_billing.get("billing_active", False)
                    else:
                        # No billing info - assume active unless deleted or guest
                        is_billable = not (member.get("deleted") or member.get("is_restricted") or member.get("is_ultra_restricted"))

                    # Determine status based on billing
                    if member.get("deleted"):
                        status = "suspended"
                    elif billable_info and not is_billable:
                        status = "inactive"  # Not billable = no active license
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
                    # Guests have a different license type
                    if member.get("is_restricted") or member.get("is_ultra_restricted"):
                        license_type = "Slack Guest"
                    else:
                        license_type = workspace_plan

                    # Parse updated timestamp as last activity approximation
                    last_activity = None
                    if member.get("updated"):
                        last_activity = datetime.fromtimestamp(member["updated"])

                    profile = member.get("profile", {})
                    email = profile.get("email", "").lower().strip()
                    name = profile.get("real_name") or profile.get("display_name") or ""

                    # Use email as external_user_id (for display) if available
                    # If no email, try to create a readable identifier from name
                    # Fall back to user_id only as last resort
                    if email:
                        external_id = email
                    elif name:
                        # No email but has name - show as "Name (U123...)"
                        external_id = f"{name} ({user_id})"
                    else:
                        external_id = user_id

                    licenses.append({
                        "external_user_id": external_id,
                        "email": email,
                        "license_type": license_type,
                        "status": status,
                        "last_activity_at": last_activity,
                        "metadata": {
                            "slack_user_id": user_id,  # Store Slack user ID for API operations
                            "email": email,
                            "name": name,
                            "title": profile.get("title"),
                            "role": role,  # Admin, Member, Guest, etc.
                            "is_admin": member.get("is_admin", False),
                            "is_owner": member.get("is_owner", False),
                            "is_guest": member.get("is_restricted", False)
                            or member.get("is_ultra_restricted", False),
                            "is_billable": is_billable,
                            "tz": member.get("tz"),
                            "has_email": bool(email),  # Track if user has email (for debugging)
                        },
                    })

                # Check for more pages
                cursor = data.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break

        # DEBUG: Log summary
        users_with_email = sum(1 for lic in licenses if lic.get("email"))
        users_without_email = sum(1 for lic in licenses if not lic.get("email"))
        logger.info(
            f"[SLACK DEBUG] Sync complete: {len(licenses)} total users, "
            f"{users_with_email} with email, {users_without_email} without email"
        )

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
