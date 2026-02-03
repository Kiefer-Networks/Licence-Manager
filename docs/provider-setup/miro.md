# Miro Integration Setup

Track Miro team members and their license types.

## Prerequisites

- Miro account with admin access
- Team or organization ownership
- API access enabled

## Setup Steps

### 1. Generate Access Token

1. Log in to [Miro](https://miro.com/)
2. Go to your profile > **Settings**
3. Navigate to **Your apps** or visit [Miro Developer](https://developers.miro.com/)
4. Click **Create new app**
5. Configure:
   - Name: "License Management"
   - Permissions: Select read access for team/organization
6. Install the app to your team
7. Copy the **Access Token**

### 2. Get Organization ID (Enterprise)

For Miro Enterprise:

1. Go to **Admin** > **Organization settings**
2. Find the Organization ID in the URL or settings

### 3. Configure in License Management

In the Settings page, add Miro provider:

- **Access Token**: Your Miro access token
- **Organization ID**: (Optional) For Enterprise organizations

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Miro user ID |
| Email | User's email address |
| Name | User's full name |
| Role | Admin, member, or guest |
| Status | Active or pending |
| License Type | Full license or free viewer |

## License Types

Miro license types:

- **Free**: Limited boards, basic features
- **Team**: Unlimited boards for team
- **Business**: Advanced features, SSO
- **Enterprise**: Full governance, analytics

User roles:
- **Admin**: Team/org administration
- **Member**: Full member access
- **Guest**: Limited access to shared boards

## Troubleshooting

### "401 Unauthorized" error

- Verify the access token is correct
- Check if the app is installed to the team
- Ensure the token has read permissions

### "403 Forbidden" error

- You may not have admin access
- Check team/organization permissions
- The app may need additional scopes

### Missing team members

- Guests may not appear in standard member lists
- Check if users are pending invitation
- Verify the correct team is selected
