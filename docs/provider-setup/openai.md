# OpenAI Integration Setup

Track OpenAI organization members and API access.

## Prerequisites

- OpenAI organization account
- Owner or admin access

## Setup Steps

### 1. Get Organization ID

1. Log in to [OpenAI Platform](https://platform.openai.com/)
2. Go to **Settings** > **Organization**
3. Copy your **Organization ID**

### 2. Create Admin API Key

1. Go to **API keys**
2. Click **Create new secret key**
3. Name: "License Management"
4. Copy the key (you won't see it again)

Note: Ensure the key has organization admin permissions to list members.

### 3. Configure in License Management

In the Settings page, add OpenAI provider:

- **Admin API Key**: Your OpenAI API key
- **Organization ID**: Your organization ID

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | OpenAI user ID |
| Email | User's email |
| Role | owner, admin, or member |
| Added Date | When added to org |

## Troubleshooting

### "Unauthorized" error

- Verify the API key has admin permissions
- Check if the key is still valid

### Missing members

- Ensure you have owner/admin access to see all members
- The API may not include pending invitations
