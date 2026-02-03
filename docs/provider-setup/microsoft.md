# Microsoft 365 Integration Setup

Track Microsoft 365 user licenses and subscriptions in your organization.

## Prerequisites

- Microsoft 365 admin access
- Azure Active Directory tenant
- Azure App Registration

## Setup Steps

### 1. Create Azure App Registration

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Configure:
   - Name: "License Management"
   - Supported account types: "Accounts in this organizational directory only"
5. Click **Register**

### 2. Configure API Permissions

1. In the app registration, go to **API permissions**
2. Click **Add a permission**
3. Select **Microsoft Graph**
4. Choose **Application permissions**
5. Add these permissions:
   - `User.Read.All`
   - `Organization.Read.All`
   - `Directory.Read.All`
6. Click **Grant admin consent**

### 3. Create Client Secret

1. Go to **Certificates & secrets**
2. Click **New client secret**
3. Add description: "License Management"
4. Select expiry period
5. Click **Add**
6. **Copy the secret value immediately** (shown only once)

### 4. Get Tenant and Client IDs

1. Go to **Overview**
2. Copy:
   - **Application (client) ID**
   - **Directory (tenant) ID**

### 5. Configure in License Management

In the Settings page, add Microsoft provider:

- **Tenant ID**: Your Azure AD tenant ID
- **Client ID**: The application (client) ID
- **Client Secret**: The secret value from step 3

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Azure AD user ID |
| Email | User principal name |
| Display Name | Full name |
| Licenses | Assigned license SKUs |
| Status | Account enabled/disabled |
| Created | Account creation date |
| Last Sign-In | Last interactive sign-in |

## License Types

Microsoft 365 licenses include:

- **Microsoft 365 E5** / **E3** / **E1**
- **Office 365 E5** / **E3** / **E1**
- **Microsoft 365 Business Premium** / **Standard** / **Basic**
- **Exchange Online Plans**
- **Teams Premium**
- And many more SKUs

## Troubleshooting

### "Insufficient privileges" error

- Verify all required API permissions are granted
- Ensure admin consent has been given
- Check that the app registration is in the correct tenant

### "Invalid client secret" error

- Client secrets expire - check the expiry date
- Create a new secret if needed
- Ensure no extra whitespace when copying

### Missing users

- Users in different Azure AD directories won't appear
- Check if users are synced from on-premises AD
- Verify the tenant ID is correct
