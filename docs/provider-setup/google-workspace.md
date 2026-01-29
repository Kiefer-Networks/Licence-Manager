# Google Workspace Integration Setup

Track Google Workspace user licenses in your organization.

## Prerequisites

- Google Workspace admin access
- Google Cloud Platform account
- Domain-wide delegation enabled

## Setup Steps

### 1. Create a Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Navigate to **IAM & Admin** > **Service Accounts**
4. Click **Create Service Account**
5. Configure:
   - Name: "License Management Service"
   - Description: "Service account for license management"
6. Click **Create and Continue**
7. Skip the optional steps and click **Done**

### 2. Generate Service Account Key

1. Click on the created service account
2. Go to **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON** format
5. Download and securely store the key file

### 3. Enable Domain-Wide Delegation

1. In the service account details, click **Show domain-wide delegation**
2. Check **Enable G Suite Domain-wide Delegation**
3. Copy the **Client ID** (a numeric ID)
4. Click **Save**

### 4. Configure Workspace Admin Console

1. Go to [Google Admin Console](https://admin.google.com/)
2. Navigate to **Security** > **API Controls** > **Domain-wide Delegation**
3. Click **Add new**
4. Enter:
   - Client ID: The numeric ID from step 3
   - OAuth Scopes:
     ```
     https://www.googleapis.com/auth/admin.directory.user.readonly
     ```
5. Click **Authorize**

### 5. Configure in License Management

In the Settings page, add Google Workspace provider:

- **Service Account JSON**: Paste the contents of the downloaded JSON key
- **Admin Email**: An admin email to impersonate (required for domain-wide delegation)
- **Domain**: Your Google Workspace domain (e.g., yourcompany.com)

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Google user ID |
| Email | Primary email |
| Name | Full name |
| Status | Active or suspended |
| Last Login | Last login time |
| Created | Account creation date |
| Org Unit | Organizational unit path |

## Troubleshooting

### "Unauthorized" error

- Verify domain-wide delegation is enabled
- Confirm the OAuth scopes are correctly configured
- Ensure the admin email has appropriate permissions

### "Quota exceeded" error

- Google Admin SDK has rate limits
- The sync may be batched automatically

### Missing users

- Check if users are in organizational units you have access to
- Verify the domain configuration is correct
