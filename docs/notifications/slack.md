# Slack Notifications Setup

Configure Slack to receive automated notifications about license management events.

## Prerequisites

- Slack workspace admin access
- Ability to create Slack apps

## Setup Steps

### 1. Create a Slack App

1. Go to [Slack API](https://api.slack.com/apps)
2. Click **Create New App**
3. Choose **From scratch**
4. Configure:
   - App Name: "License Management Notifications"
   - Workspace: Select your workspace
5. Click **Create App**

### 2. Configure Bot Permissions

1. In the app settings, go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `chat:write` - Send messages to channels
   - `channels:read` - List public channels

### 3. Install the App

1. Go to **Install App** in the sidebar
2. Click **Install to Workspace**
3. Review and authorize the permissions
4. Copy the **Bot User OAuth Token** (starts with `xoxb-`)

### 4. Invite Bot to Channels

For each channel where you want notifications:
1. Open the channel in Slack
2. Type `/invite @YourAppName`
3. Or click the channel name → Integrations → Add apps

### 5. Configure in License Management

1. Go to **Settings** → **Notifications** tab
2. Enter the Bot Token in the Slack configuration section
3. Click **Save** to test the connection

## Notification Rules

### Creating Rules

1. In **Settings** → **Notifications**, click **Add Rule**
2. Configure:
   - **Event Type**: Select the event to monitor
   - **Channel**: Slack channel ID or name (e.g., `#license-alerts`)
   - **Enabled**: Toggle to activate/deactivate
   - **Custom Message** (optional): Override the default message template

### Available Event Types

| Event | Description |
|-------|-------------|
| Employee Offboarded | Employee marked as offboarded still has active licenses |
| License Inactive | License unused for more than 30 days |
| License Expiring | License approaching expiration date |
| Sync Error | Provider synchronization failed |
| Payment Expiring | Payment method approaching expiration |

### Channel Format

You can specify the channel in two ways:
- Channel name: `#general` or `general`
- Channel ID: `C01234ABCDE` (recommended for reliability)

To find a channel ID:
1. Right-click the channel in Slack
2. Click **View channel details**
3. Scroll to the bottom to find the Channel ID

## User Notification Preferences

Individual users can customize their notification preferences:

1. Go to **Profile** → **Notifications** tab
2. For each event type:
   - Enable/disable receiving notifications
   - Choose delivery method (channel or DM)
   - Specify a custom channel

## Automated Checks

The system runs automated checks:

| Check | Frequency | Description |
|-------|-----------|-------------|
| Inactive Licenses | Daily | Finds licenses inactive >30 days |
| Offboarded Employees | Every 6 hours | Detects offboarded staff with active licenses |
| Expiring Licenses | Daily | Identifies licenses expiring within threshold |

## Testing Notifications

1. Go to **Settings** → **Notifications**
2. Enter a channel name in the test section
3. Click **Send Test Notification**
4. Verify the message appears in Slack

## Message Format

Notifications include:
- Event type indicator with emoji
- Affected entity (employee, license, provider)
- Relevant details (dates, counts, etc.)
- Timestamp

Example:
```
⚠️ Employee Offboarded Alert

John Doe (john@company.com) has been marked as offboarded but still has 3 active licenses.

Providers: GitHub, Slack, JetBrains
```

## Troubleshooting

### "channel_not_found" Error

- Ensure the bot is invited to the channel
- Use the channel ID instead of the name
- Check the channel exists and is not archived

### "not_authed" or "invalid_auth" Error

- Verify the bot token is correct
- Check the token starts with `xoxb-`
- Ensure the app is still installed to the workspace

### No Notifications Received

- Verify the notification rule is enabled
- Check that the event conditions are met
- Review the automation schedule (some checks run daily)
- Ensure the Slack configuration is saved and connected

### Messages Not Formatted Correctly

- Slack Block Kit formatting may vary by client
- Plain text fallback is always included

## Security Considerations

- Bot tokens have limited permissions (chat:write only)
- Tokens are stored encrypted in the database
- No user data is shared with Slack beyond notifications
- Channel access is controlled by Slack workspace admins
