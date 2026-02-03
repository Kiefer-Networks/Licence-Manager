# Hugging Face Integration Setup

Track Hugging Face organization members and their access levels.

## Prerequisites

- Hugging Face organization account
- Admin access to your organization
- Access token with read permissions

## Setup Steps

### 1. Generate Access Token

1. Log in to [Hugging Face](https://huggingface.co/)
2. Go to **Settings** > **Access Tokens**
3. Click **New token**
4. Configure:
   - Name: "License Management"
   - Type: Select **Read** (minimum required)
5. Click **Generate token**
6. Copy the token (starts with `hf_`)

### 2. Get Organization Name

Your organization name is in the URL:
```
https://huggingface.co/{organization-name}
```

### 3. Configure in License Management

In the Settings page, add Hugging Face provider:

- **Access Token**: Your Hugging Face access token
- **Organization**: Your organization name/slug

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Hugging Face user ID |
| Username | Hugging Face username |
| Email | Verified email (if available) |
| Full Name | User's full name |
| Role | admin, write, contributor, or read |
| Pro Status | Whether user has Pro subscription |
| 2FA Status | Two-factor authentication enabled |
| External | Whether user is external collaborator |
| Resource Groups | Group memberships (Enterprise) |

## License Types

The integration maps Hugging Face roles to license types:

| Hugging Face Role | License Type | Permissions |
|-------------------|--------------|-------------|
| `admin` | Admin | Full access, billing, member management |
| `write` | Write | Create and modify repos |
| `contributor` | Contributor | Push to repos |
| `read` | Read | View private repos |

## Resource Groups (Enterprise)

For Hugging Face Enterprise organizations, resource groups are also tracked:

- Group name and ID
- User's role within each group
- Enables granular access control

## API Endpoint Used

The integration uses:

- `GET /api/organizations/{name}/members` - List organization members

Supports pagination for large organizations (500 members per page).

## Troubleshooting

### "401 Unauthorized" error

- Verify the access token is correct
- Ensure the token has not expired
- Check that the token has read permissions

### "403 Forbidden" error

- You may not have access to the organization
- Ensure you are a member of the organization
- Admin access may be required for full member list

### "404 Not Found" error

- Verify the organization name is correct
- Check for typos (case-sensitive)
- Ensure the organization exists

### Missing members

- External collaborators may have limited visibility
- Some members may not have verified emails
- Check if members are in resource groups with restricted access

### Missing email addresses

- Only verified emails are returned
- Users can choose not to verify their email
- Email field may be null for some users
