# Zoom Integration Setup

Track Zoom user licenses in your organization.

## Prerequisites

- Zoom account with admin access
- Zoom Marketplace access
- Server-to-Server OAuth app

## Setup Steps

### 1. Create Server-to-Server OAuth App

1. Go to [Zoom App Marketplace](https://marketplace.zoom.us/)
2. Click **Develop** > **Build App**
3. Select **Server-to-Server OAuth**
4. Click **Create**
5. Name: "License Management"

### 2. Configure App

1. In **App Credentials**, copy:
   - **Account ID**
   - **Client ID**
   - **Client Secret**

### 3. Add Scopes

1. Go to **Scopes** tab
2. Click **Add Scopes**
3. Add these scopes:
   - `user:read:list_users:admin`
   - `user:read:user:admin`
4. Click **Done**

### 4. Activate App

1. Go to **Activation** tab
2. Click **Activate your app**
3. Confirm activation

### 5. Configure in License Management

In the Settings page, add Zoom provider:

- **Account ID**: Your Zoom account ID
- **Client ID**: The OAuth client ID
- **Client Secret**: The OAuth client secret

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Zoom user ID |
| Email | User's email address |
| Name | First and last name |
| Type | Basic, Licensed, or On-Prem |
| Status | Active, inactive, or pending |
| Department | User's department |
| Role | User's role in Zoom |
| Last Login | Last client login time |
| Created | Account creation date |

## License Types

Zoom license types include:

- **Basic**: Free account (100 participants, 40 min limit)
- **Pro**: Licensed user (300 participants, unlimited)
- **Business**: Business license
- **Enterprise**: Enterprise license
- **Zoom Rooms**: Room license
- **Zoom Phone**: Phone license

## Troubleshooting

### "Invalid credentials" error

- Verify Account ID, Client ID, and Client Secret
- Ensure the app is activated
- Check that scopes are correctly assigned

### "Insufficient privileges" error

- The app needs admin-level scopes
- Verify you have account admin access
- Re-add the required scopes

### Missing users

- Check if users are pending invitation
- Verify user status (active vs inactive)
- Some users may be in sub-accounts
