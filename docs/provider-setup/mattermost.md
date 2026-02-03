# Mattermost Integration Setup

Track Mattermost server users and their status.

## Prerequisites

- Mattermost server with admin access
- System admin account
- Personal access token or session token

## Setup Steps

### 1. Enable Personal Access Tokens

1. Log in to Mattermost as System Admin
2. Go to **System Console** > **Integrations** > **Integration Management**
3. Enable **Enable Personal Access Tokens**
4. Save settings

### 2. Generate Personal Access Token

1. Click your profile picture > **Profile**
2. Go to **Security** > **Personal Access Tokens**
3. Click **Create Token**
4. Description: "License Management"
5. Click **Save**
6. Copy the **Access Token**

### 3. Get Server URL

Note your Mattermost server URL:
```
https://mattermost.yourcompany.com
```

### 4. Configure in License Management

In the Settings page, add Mattermost provider:

- **Access Token**: Your personal access token
- **Server URL**: Your Mattermost server URL

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Mattermost user ID |
| Email | User's email address |
| Username | Mattermost username |
| Name | First and last name |
| Status | Active, inactive, or deactivated |
| Roles | System roles (admin, user) |
| Position | Job title |
| Created | Account creation date |
| Last Activity | Last active time |

## License Types

Mattermost editions:

- **Free**: Basic team messaging
- **Professional**: Advanced permissions, SSO
- **Enterprise**: Compliance, high availability

User roles:
- **System Admin**: Full system access
- **Team Admin**: Team management
- **Member**: Standard user

## Self-Hosted Considerations

For self-hosted Mattermost:

- Ensure API access is enabled
- Check that your network allows API connections
- Consider firewall rules for external access

## Troubleshooting

### "401 Unauthorized" error

- Verify the access token is correct
- Check that personal access tokens are enabled
- Ensure the token hasn't been revoked

### "Connection refused" error

- Verify the server URL
- Check that the server is accessible
- Ensure HTTPS is configured if required

### "403 Forbidden" error

- Your account may not have system admin permissions
- Check user permissions in System Console
- Personal access tokens may be disabled

### Missing users

- Deactivated users may not appear
- Check if users are in different teams
- Guest accounts may be excluded
