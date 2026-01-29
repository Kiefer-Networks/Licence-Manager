# Slack Integration Setup

Track Slack workspace members and send notifications.

## Prerequisites

- Slack workspace admin access
- Ability to create Slack apps

## Setup Steps

### 1. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Configure:
   - App Name: "License Management"
   - Workspace: Select your workspace
5. Click **Create App**

### 2. Configure Bot Permissions

1. In the app settings, go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `users:read` - View users in the workspace
   - `users:read.email` - View email addresses
   - `chat:write` - Send messages (for notifications)
   - `channels:read` - View channels (for notifications)

### 3. Install the App

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Review and authorize the permissions
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 4. (Optional) Add User Token for SCIM

For Enterprise Grid with SCIM, you may need a user token:

1. Under **User Token Scopes**, add:
   - `admin.users:read`
2. Re-install the app
3. Copy the **User OAuth Token** (starts with `xoxp-`)

### 5. Configure in License Management

In the Settings page, add Slack provider:

- **Bot Token**: The `xoxb-` token
- **User Token**: (Optional) The `xoxp-` token for SCIM

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Slack member ID |
| Email | User's email |
| Name | Display name |
| Status | Active or deactivated |
| Role | Admin, owner, or member |
| Is Guest | Single or multi-channel guest |

## Notifications

The Slack integration also enables notifications:

1. Go to **Settings** > **Notifications**
2. Create notification rules for:
   - Employee offboarded
   - License inactive
   - Sync errors
3. Specify the Slack channel for each rule

## Troubleshooting

### "missing_scope" error

- Verify all required scopes are added
- Re-install the app after adding scopes

### "channel_not_found" error

- Ensure the bot is added to the channel
- Use the channel ID instead of the name

### Missing members

- Check if the bot has access to guest users
- Verify the workspace has the members you expect
