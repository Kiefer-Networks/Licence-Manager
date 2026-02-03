# Auth0 Integration Setup

Track Auth0 tenant users and their application access.

## Prerequisites

- Auth0 tenant with admin access
- Management API enabled
- Machine-to-Machine application

## Setup Steps

### 1. Create Machine-to-Machine Application

1. Log in to [Auth0 Dashboard](https://manage.auth0.com/)
2. Go to **Applications** > **Applications**
3. Click **Create Application**
4. Name: "License Management"
5. Type: **Machine to Machine Applications**
6. Click **Create**

### 2. Authorize Management API

1. In the application settings, go to **APIs** tab
2. Find **Auth0 Management API**
3. Toggle to authorize
4. Select these scopes:
   - `read:users`
   - `read:user_idp_tokens`
   - `read:organizations`
   - `read:organization_members`
5. Click **Update**

### 3. Get Credentials

1. Go to the **Settings** tab
2. Copy:
   - **Domain** (e.g., `your-tenant.auth0.com`)
   - **Client ID**
   - **Client Secret**

### 4. Configure in License Management

In the Settings page, add Auth0 provider:

- **Domain**: Your Auth0 domain
- **Client ID**: The M2M application client ID
- **Client Secret**: The application client secret

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Auth0 user ID |
| Email | User's email address |
| Name | User's full name |
| Connection | Identity provider (database, social, etc.) |
| Last Login | Last authentication time |
| Login Count | Total number of logins |
| Created | Account creation date |

## Troubleshooting

### "401 Unauthorized" error

- Verify Client ID and Client Secret are correct
- Check the domain format (should not include `https://`)
- Ensure the M2M application is not disabled

### "403 Forbidden" error

- Verify the Management API is authorized
- Check that all required scopes are granted
- The application may need to be re-authorized

### "Rate limit exceeded" error

- Auth0 has rate limits on Management API
- Sync will automatically retry with backoff

### Missing users

- Check if users are in different connections
- Verify organization members if using organizations
- Some social connections may have limited data
