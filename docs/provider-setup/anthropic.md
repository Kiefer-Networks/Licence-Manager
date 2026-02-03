# Anthropic Integration Setup

Track Anthropic (Claude) API users and API keys in your organization.

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

### Users

| Field | Description |
|-------|-------------|
| User ID | Anthropic user ID |
| Email | User's email address |
| Name | User's full name |
| Role | User role (see below) |
| Added At | When user joined the organization |

### API Keys

| Field | Description |
|-------|-------------|
| Key ID | API key identifier |
| Key Name | Name of the API key |
| Status | Active or disabled |
| Created At | When the key was created |
| Last Used | Last usage timestamp |
| Workspace | Associated workspace ID |

## License Types

The integration maps Anthropic roles to license types:

| Anthropic Role | License Type |
|----------------|--------------|
| `admin` | Admin |
| `developer` | Developer |
| `billing` | Billing |
| `user` | User |
| `claude_code_user` | Claude Code User |
| API Key (no user) | API Key |

## API Endpoints Used

The integration uses the following Admin API endpoints:

- `GET /v1/organizations/users` - List organization users
- `GET /v1/organizations/api_keys` - List API keys

Both endpoints support pagination for large organizations.

## Troubleshooting

### "401 Unauthorized" error

- Verify the API key is correct
- Ensure you're using an **Admin** API key (not a regular API key)
- Admin keys start with `sk-ant-admin-`

### "403 Forbidden" error

- Your account may not have organization admin permissions
- Only organization admins can create Admin API keys
- Contact your organization admin to grant access

### Missing users

- Users must accept their invitation to appear
- Check if users are in different workspaces
- Ensure the Admin API key has organization-level access

### API keys not showing

- API key listing requires admin permissions
- Some API keys may be workspace-specific
