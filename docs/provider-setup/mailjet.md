# Mailjet Integration Setup

Track Mailjet account users and sub-accounts.

## Prerequisites

- Mailjet account with admin access
- API key and secret
- Master account (for sub-account tracking)

## Setup Steps

### 1. Get API Credentials

1. Log in to [Mailjet](https://app.mailjet.com/)
2. Go to **Account Settings** > **API Key Management**
3. You'll see your:
   - **API Key** (public key)
   - **API Secret** (private key)
4. Copy both values

If you don't have an API key:
1. Click **Generate a new API Key**
2. Note: Generate with full permissions for user management

### 2. Configure in License Management

In the Settings page, add Mailjet provider:

- **API Key**: Your Mailjet API key
- **API Secret**: Your Mailjet API secret

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Mailjet user/contact ID |
| Email | Account email address |
| Name | Account name |
| Status | Active or inactive |
| Created | Account creation date |

## License Types

Mailjet pricing tiers:

- **Free**: Limited emails/day
- **Essential**: Basic email features
- **Premium**: Advanced analytics, A/B testing
- **Custom**: Enterprise volume

For master accounts with sub-accounts, each sub-account is tracked separately.

## API Authentication

Mailjet uses HTTP Basic Authentication:

- Username: API Key
- Password: API Secret

The integration handles this automatically.

## Troubleshooting

### "401 Unauthorized" error

- Verify the API key and secret are correct
- Check that the API key is active
- Ensure no extra whitespace in credentials

### "403 Forbidden" error

- Your API key may have limited permissions
- Generate a new key with full access
- Check account status in Mailjet dashboard

### Missing sub-accounts

- Only master accounts can see sub-accounts
- Verify you're using master account credentials
- Sub-accounts must be active to appear
