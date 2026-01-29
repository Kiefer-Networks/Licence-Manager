# Figma Integration Setup

Track Figma organization or team members.

## Prerequisites

- Figma organization or team
- Admin access

## Setup Steps

### 1. Generate Access Token

1. Log in to [Figma](https://www.figma.com/)
2. Go to **Account Settings**
3. Scroll to **Personal access tokens**
4. Click **Create new token**
5. Name: "License Management"
6. Copy the token

### 2. Get Organization ID (Enterprise)

For Figma Enterprise:

1. Go to your organization settings
2. Find the Organization ID in the URL or settings

### 3. Configure in License Management

In the Settings page, add Figma provider:

- **Access Token**: Your Figma personal access token
- **Organization ID**: (Optional) Your organization ID for Enterprise

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Figma user ID |
| Email | User's email |
| Handle | Figma username |
| Role | Owner, admin, editor, or viewer |
| License Type | Professional or Viewer |

## License Types

Figma has different license types:

- **Professional**: Full editing access
- **Viewer**: View and comment only

The integration determines license type based on user role.

## Troubleshooting

### "Unauthorized" error

- Verify the access token is correct
- Check if the token has expired

### Limited member list

- Personal tokens may have limited org access
- For full org access, Enterprise features may be required
