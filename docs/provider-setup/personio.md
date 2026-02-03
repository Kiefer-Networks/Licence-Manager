# Personio Integration Setup

Track Personio HR system employees and their attributes.

## Prerequisites

- Personio account with admin access
- API credentials enabled
- Company administrator permissions

## Setup Steps

### 1. Enable API Access

1. Log in to [Personio](https://www.personio.de/) as admin
2. Go to **Settings** > **Integrations** > **API credentials**
3. Click **Generate new credentials**
4. Configure:
   - Name: "License Management"
   - Permissions: Select employee read access
5. Click **Generate**

### 2. Get Credentials

1. Copy the **Client ID**
2. Copy the **Client Secret**

**Note:** The client secret is only shown once. Store it securely.

### 3. Configure in License Management

In the Settings page, add Personio provider:

- **Client ID**: Your Personio client ID
- **Client Secret**: Your Personio client secret

## Data Synced

| Field | Description |
|-------|-------------|
| Employee ID | Personio employee ID |
| Email | Work email address |
| Name | First and last name |
| Status | Active, inactive, or onboarding |
| Position | Job title |
| Department | Department name |
| Office | Office location |
| Supervisor | Direct manager |
| Start Date | Employment start date |
| End Date | Employment end date (if applicable) |

## Employee Status

Personio employee statuses:

- **Active**: Currently employed
- **Inactive**: Left the company
- **Onboarding**: Not yet started
- **Leave**: On extended leave

## API Authentication

Personio uses OAuth 2.0 Client Credentials:

1. Exchange credentials for access token
2. Use token for API requests
3. Tokens are automatically refreshed

## Troubleshooting

### "401 Unauthorized" error

- Verify Client ID and Client Secret are correct
- Check that credentials haven't been revoked
- Regenerate credentials if needed

### "403 Forbidden" error

- API credentials may lack required permissions
- Check that employee read access is granted
- Verify admin permissions in Personio

### Missing employees

- Check employee status filters
- Inactive employees may be excluded
- Verify department/office access permissions

### "Rate limit exceeded" error

- Personio has API rate limits
- Sync will automatically handle pagination
- Large organizations may need batched sync
