"""Provider domain model."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ProviderName(StrEnum):
    """Provider name enum."""

    HIBOB = "hibob"
    CURSOR = "cursor"
    FIGMA = "figma"
    GITHUB = "github"
    GITLAB = "gitlab"
    GOOGLE_WORKSPACE = "google_workspace"
    JETBRAINS = "jetbrains"
    MANUAL = "manual"
    MATTERMOST = "mattermost"
    MICROSOFT = "microsoft"
    MIRO = "miro"
    ONEPASSWORD = "1password"
    OPENAI = "openai"
    SLACK = "slack"


class ProviderType(StrEnum):
    """Provider type - how licenses are managed."""

    API = "api"  # Automatic sync via API (Cursor, JetBrains, etc.)
    MANUAL = "manual"  # Manual entry (Royal Apps, etc.)


class LicenseModel(StrEnum):
    """License model - how licenses work."""

    SEAT_BASED = "seat_based"  # Remove user = free seat (Cursor)
    LICENSE_BASED = "license_based"  # Licenses exist independently (JetBrains)


class BillingCycle(StrEnum):
    """Billing cycle for licenses."""

    MONTHLY = "monthly"
    YEARLY = "yearly"
    PERPETUAL = "perpetual"  # One-time purchase, no renewal
    ONE_TIME = "one_time"  # One-time with possible upgrade fees


class SyncStatus(StrEnum):
    """Sync status enum."""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"


class ProviderConfig(BaseModel):
    """Provider configuration model."""

    # HiBob
    hibob_api_key: str | None = None
    hibob_service_user_id: str | None = None

    # Google Workspace
    google_service_account_json: str | None = None
    google_admin_email: str | None = None
    google_domain: str | None = None

    # OpenAI
    openai_admin_api_key: str | None = None
    openai_org_id: str | None = None

    # Figma
    figma_access_token: str | None = None
    figma_org_id: str | None = None

    # Cursor
    cursor_api_key: str | None = None
    cursor_team_id: str | None = None

    # Slack
    slack_bot_token: str | None = None
    slack_user_token: str | None = None


class Provider(BaseModel):
    """Provider domain model."""

    id: UUID
    name: ProviderName
    display_name: str
    enabled: bool = True
    config: dict[str, Any] | None = None
    last_sync_at: datetime | None = None
    last_sync_status: SyncStatus | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic config."""

        from_attributes = True
