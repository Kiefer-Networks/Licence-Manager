# GitHub Integration Setup

Track GitHub organization members and their access levels.

## Prerequisites

- GitHub organization with admin access
- Personal Access Token or GitHub App
- Organization owner permissions

## Setup Steps

### 1. Create Personal Access Token (Classic)

1. Log in to [GitHub](https://github.com/)
2. Go to **Settings** > **Developer settings**
3. Select **Personal access tokens** > **Tokens (classic)**
4. Click **Generate new token** > **Generate new token (classic)**
5. Name: "License Management"
6. Select scopes:
   - `read:org`
   - `read:user`
   - `user:email`
7. Click **Generate token**
8. Copy the token

### 2. Identify Organization

Note your organization name from the URL:
```
https://github.com/{org-name}
```

### 3. Configure in License Management

In the Settings page, add GitHub provider:

- **Access Token**: Your GitHub personal access token
- **Organization Name**: Your GitHub organization name

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | GitHub user ID |
| Login | GitHub username |
| Email | User's email (if public) |
| Name | User's full name |
| Role | Owner, admin, or member |
| 2FA | Two-factor authentication status |
| Created | Account creation date |

## License Types

GitHub organization plans:

- **Free**: Public and private repos, basic features
- **Team**: Advanced collaboration features
- **Enterprise**: Advanced security, compliance, deployment

GitHub user roles:
- **Owner**: Full administrative access
- **Admin**: Repository administration
- **Member**: Standard access

## Troubleshooting

### "401 Bad credentials" error

- Verify the access token is correct
- Check that the token hasn't expired
- Ensure the token has required scopes

### "404 Not Found" error

- Verify the organization name is correct
- Ensure you have access to the organization
- Check for typos (case-sensitive)

### Missing members

- External collaborators may not appear in member list
- Check if SAML SSO is required for access
- Pending invitations won't appear as members

### Missing email addresses

- GitHub only shows public emails
- Users can hide their email in privacy settings
- Email may be null for some users
