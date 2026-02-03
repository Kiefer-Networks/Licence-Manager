# Atlassian Integration Setup

Track Atlassian Cloud (Jira, Confluence, etc.) user licenses in your organization.

## Prerequisites

- Atlassian organization admin access
- Atlassian Cloud account
- Organization API enabled

## Setup Steps

### 1. Create API Token

1. Log in to [Atlassian Account](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. Label: "License Management"
4. Click **Create**
5. Copy the token

### 2. Get Organization ID

1. Go to [Atlassian Admin](https://admin.atlassian.com/)
2. Select your organization
3. The Organization ID is in the URL:
   ```
   https://admin.atlassian.com/o/{organization-id}/...
   ```

### 3. Configure in License Management

In the Settings page, add Atlassian provider:

- **API Token**: Your Atlassian API token
- **Organization ID**: The organization ID from the URL
- **Admin Email**: Your Atlassian admin email address

## Data Synced

| Field | Description |
|-------|-------------|
| Account ID | Atlassian account ID |
| Email | User's email address |
| Display Name | User's full name |
| Status | Active or inactive |
| Products | Jira, Confluence, etc. |
| Last Active | Last activity timestamp |

## License Types

Atlassian Cloud licenses include:

- **Jira Software** (Standard, Premium, Enterprise)
- **Confluence** (Standard, Premium, Enterprise)
- **Jira Service Management**
- **Jira Work Management**
- **Trello** (Enterprise)
- **Bitbucket** (Standard, Premium)

## API Rate Limits

The Atlassian Admin API has rate limits:

- 100 requests per minute per organization
- Sync will automatically handle pagination

## Troubleshooting

### "401 Unauthorized" error

- Verify the API token is correct
- Ensure the admin email matches the token owner
- Check that the token hasn't been revoked

### "403 Forbidden" error

- Verify organization admin permissions
- The Organization API must be enabled
- Check the organization ID is correct

### Missing users

- Only managed accounts appear in the organization API
- External/guest users may not be included
- Verify users are in the correct organization
