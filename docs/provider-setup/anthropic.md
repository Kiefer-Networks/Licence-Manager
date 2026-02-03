# Anthropic Integration Setup

Track Anthropic (Claude) API usage and workspace members.

## Prerequisites

- Anthropic organization account
- Admin access to your organization
- Admin API key

## Setup Steps

### 1. Generate Admin API Key

1. Log in to [Anthropic Console](https://console.anthropic.com/)
2. Go to **Settings** > **Admin API keys**
3. Click **Create Admin API Key**
4. Name: "License Management"
5. Copy the API key (starts with `sk-ant-admin-`)

**Note:** Admin API keys provide organization-level access. Keep them secure.

### 2. Configure in License Management

In the Settings page, add Anthropic provider:

- **Admin API Key**: Your admin API key (starting with `sk-ant-admin-`)

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Anthropic user ID |
| Email | User's email address |
| Name | User's full name |
| Role | Admin or member |
| Status | Active or invited |
| Workspaces | Workspace memberships |

## API Access

The Admin API provides:

- Organization member listing
- Workspace information
- User role management

## Troubleshooting

### "401 Unauthorized" error

- Verify the API key is correct
- Ensure you're using an **Admin** API key (not a regular API key)
- Admin keys start with `sk-ant-admin-`

### "403 Forbidden" error

- Your account may not have organization admin permissions
- Contact your organization admin to grant access

### Missing workspace members

- Members must accept their invitation to appear
- Check if members are in different workspaces
