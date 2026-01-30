"""Built-in provider logos for common SaaS providers."""

# Map provider name (lowercase) to logo URL
# These are SVG logos from common CDNs or can be replaced with self-hosted versions
BUILT_IN_LOGOS: dict[str, str] = {
    # Microsoft
    "microsoft": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
    "microsoft365": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
    "azure": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Microsoft_Azure.svg",

    # Google
    "google": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "google_workspace": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "googleworkspace": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",

    # Communication
    "slack": "https://upload.wikimedia.org/wikipedia/commons/d/d5/Slack_icon_2019.svg",
    "zoom": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Zoom_Communications_Logo.svg",
    "teams": "https://upload.wikimedia.org/wikipedia/commons/c/c9/Microsoft_Office_Teams_%282018%E2%80%93present%29.svg",

    # Development
    "github": "https://upload.wikimedia.org/wikipedia/commons/9/91/Octicons-mark-github.svg",
    "gitlab": "https://upload.wikimedia.org/wikipedia/commons/e/e1/GitLab_logo.svg",
    "bitbucket": "https://upload.wikimedia.org/wikipedia/commons/0/0e/Bitbucket-blue-logomark-only.svg",
    "jira": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Jira_Logo.svg",
    "confluence": "https://upload.wikimedia.org/wikipedia/commons/8/8a/Confluence-blue-logo-gradient-rgb%402x.png",
    "atlassian": "https://upload.wikimedia.org/wikipedia/commons/2/2c/Atlassian-logo-blue-large.svg",

    # Cloud / Infrastructure
    "aws": "https://upload.wikimedia.org/wikipedia/commons/9/93/Amazon_Web_Services_Logo.svg",
    "digitalocean": "https://upload.wikimedia.org/wikipedia/commons/f/ff/DigitalOcean_logo.svg",
    "heroku": "https://upload.wikimedia.org/wikipedia/commons/e/ec/Heroku_logo.svg",

    # Design
    "figma": "https://upload.wikimedia.org/wikipedia/commons/3/33/Figma-logo.svg",
    "adobe": "https://upload.wikimedia.org/wikipedia/commons/7/7b/Adobe_Systems_logo_and_wordmark.svg",
    "canva": "https://upload.wikimedia.org/wikipedia/commons/0/08/Canva_icon_2021.svg",

    # CRM / Sales
    "salesforce": "https://upload.wikimedia.org/wikipedia/commons/f/f9/Salesforce.com_logo.svg",
    "hubspot": "https://upload.wikimedia.org/wikipedia/commons/3/3f/HubSpot_Logo.svg",

    # HR
    "hibob": "https://cdn.hibob.com/hubfs/Brand/Bob_Logo_Black.svg",
    "workday": "https://upload.wikimedia.org/wikipedia/commons/8/80/Workday_logo.svg",

    # Security
    "okta": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Okta_logo.svg",
    "1password": "https://upload.wikimedia.org/wikipedia/commons/e/e0/1Password_logo_2022.svg",
    "lastpass": "https://upload.wikimedia.org/wikipedia/commons/c/ce/LastPass_logo.svg",

    # Productivity
    "notion": "https://upload.wikimedia.org/wikipedia/commons/4/45/Notion_app_logo.png",
    "asana": "https://upload.wikimedia.org/wikipedia/commons/3/3b/Asana_logo.svg",
    "trello": "https://upload.wikimedia.org/wikipedia/commons/1/17/Trello-logo-blue.svg",
    "monday": "https://upload.wikimedia.org/wikipedia/commons/c/c6/Monday_logo.svg",

    # Other
    "dropbox": "https://upload.wikimedia.org/wikipedia/commons/7/78/Dropbox_Icon.svg",
    "box": "https://upload.wikimedia.org/wikipedia/commons/5/57/Box%2C_Inc._logo.svg",
    "docusign": "https://upload.wikimedia.org/wikipedia/commons/a/a4/DocuSign_Logo.svg",

    # Manual/Custom
    "manual": None,  # No default logo for manual providers
}


def get_provider_logo(provider_name: str, custom_logo_url: str | None = None) -> str | None:
    """Get logo URL for a provider.

    Args:
        provider_name: Provider name (will be lowercased for lookup)
        custom_logo_url: Custom logo URL set by user

    Returns:
        Logo URL or None if no logo available
    """
    if custom_logo_url:
        return custom_logo_url

    return BUILT_IN_LOGOS.get(provider_name.lower())
