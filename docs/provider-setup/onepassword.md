# 1Password Integration Setup

Track 1Password team members using the SCIM bridge.

## Prerequisites

- 1Password Business or Enterprise account
- 1Password SCIM bridge deployed
- Admin access

## Setup Steps

### 1. Deploy SCIM Bridge

1Password uses SCIM for provisioning. You need to deploy the SCIM bridge:

1. Log in to [1Password Business](https://start.1password.com/)
2. Go to **Integrations** > **Directory**
3. Click **SCIM bridge**
4. Follow the deployment guide for your environment:
   - Docker
   - Kubernetes
   - Cloud Run
   - Azure Container Apps

### 2. Get SCIM Bridge URL

After deployment, note your SCIM bridge URL:
```
https://scim.yourcompany.com
```

Or use the 1Password-hosted option:
```
https://your-account.1password.com/scim/v2
```

### 3. Generate Bearer Token

1. In SCIM bridge setup, generate a bearer token
2. This token authenticates API requests
3. Store it securely

### 4. Configure in License Management

In the Settings page, add 1Password provider:

- **API Token**: Your SCIM bearer token
- **Sign-in Address**: Your SCIM bridge URL

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | 1Password user ID |
| Email | User's email address |
| Name | User's full name |
| Status | Active or suspended |
| State | Provisioned state |
| Groups | Team/vault memberships |

## License Types

1Password plans:

- **Teams**: Up to 10 users
- **Business**: Unlimited users, advanced features
- **Enterprise**: Custom deployment, dedicated support

User states:
- **Active**: Full access
- **Suspended**: Account suspended
- **Invited**: Pending activation

## SCIM Bridge Endpoints

The integration uses these SCIM endpoints:

- `GET /Users` - List all users
- `GET /Groups` - List all groups
- `GET /Users/{id}` - Get specific user

## Troubleshooting

### "401 Unauthorized" error

- Verify the bearer token is correct
- Check that the token hasn't been revoked
- Ensure the SCIM bridge is running

### "Connection refused" error

- Verify the SCIM bridge URL
- Check that the bridge is accessible
- Ensure HTTPS is configured correctly

### Missing users

- Check if users are provisioned through SCIM
- Verify group memberships
- Users must be confirmed to appear
