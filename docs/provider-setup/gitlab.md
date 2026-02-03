# GitLab Integration Setup

Track GitLab group members and their access levels.

## Prerequisites

- GitLab group with owner/maintainer access
- Personal Access Token
- GitLab.com or self-hosted instance

## Setup Steps

### 1. Create Personal Access Token

1. Log in to your GitLab instance
2. Go to **User Settings** > **Access Tokens**
3. Click **Add new token**
4. Configure:
   - Name: "License Management"
   - Expiration: Set appropriate date
   - Scopes: Select `read_api`
5. Click **Create personal access token**
6. Copy the token

### 2. Get Group ID

1. Navigate to your group
2. Go to **Settings** > **General**
3. Find the **Group ID** (numeric)

Or from the URL:
- Groups: `https://gitlab.com/groups/{group-name}` (use group name)
- Subgroups: Note the full path

### 3. Configure in License Management

In the Settings page, add GitLab provider:

- **Access Token**: Your GitLab personal access token
- **Group ID**: Your group ID or path
- **Base URL**: (Optional) For self-hosted: `https://gitlab.yourcompany.com`

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | GitLab user ID |
| Username | GitLab username |
| Email | User's email address |
| Name | User's full name |
| State | Active, blocked, or deactivated |
| Access Level | Guest, Reporter, Developer, Maintainer, Owner |
| Created | Account creation date |

## Access Levels

GitLab access levels:

- **Guest** (10): View issues and wiki
- **Reporter** (20): View code and CI/CD
- **Developer** (30): Push code, manage issues
- **Maintainer** (40): Manage project settings
- **Owner** (50): Full group control

## Self-Hosted GitLab

For self-hosted instances:

1. Ensure your instance allows API access
2. Set the **Base URL** to your GitLab URL
3. Use HTTPS for secure connections

## Troubleshooting

### "401 Unauthorized" error

- Verify the access token is correct
- Check that the token hasn't expired
- Ensure `read_api` scope is granted

### "404 Not Found" error

- Verify the group ID is correct
- Check access to the group
- For self-hosted, verify the base URL

### "403 Forbidden" error

- You may not have sufficient permissions
- The group may require higher access level
- Check if IP restrictions are in place

### Missing members

- Only direct members appear by default
- Inherited members from parent groups may need separate sync
- Check if members are blocked or deactivated
