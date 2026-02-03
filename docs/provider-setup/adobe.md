# Adobe Integration Setup

Track Adobe Creative Cloud and Document Cloud licenses in your organization.

## Prerequisites

- Adobe Admin Console access
- Adobe Developer Console access
- Server-to-Server OAuth credentials

## Setup Steps

### 1. Create Project in Adobe Developer Console

1. Go to [Adobe Developer Console](https://developer.adobe.com/console/)
2. Click **Create new project**
3. Name: "License Management"
4. Click **Add API**

### 2. Add User Management API

1. Select **User Management API**
2. Click **Next**
3. Choose **OAuth Server-to-Server**
4. Click **Save configured API**

### 3. Gather Credentials

1. In the project, go to **OAuth Server-to-Server**
2. Copy:
   - **Client ID**
   - **Client Secret**
   - **Technical Account ID** (in the credentials details)

### 4. Get Organization ID

1. Go to [Adobe Admin Console](https://adminconsole.adobe.com/)
2. Click on your organization name (top right)
3. Go to **Settings** > **Identity**
4. Copy the **Organization ID**

### 5. Configure in License Management

In the Settings page, add Adobe provider:

- **Client ID**: The OAuth client ID
- **Client Secret**: The OAuth client secret
- **Organization ID**: Your Adobe organization ID
- **Technical Account ID**: The technical account ID

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Adobe user ID |
| Email | User's email address |
| Name | First and last name |
| Status | Active or disabled |
| Type | Federated, Enterprise, or Adobe ID |
| Products | Assigned product configurations |
| Groups | User group memberships |

## License Types

Adobe licenses include:

- **Creative Cloud All Apps**
- **Creative Cloud Single App** (Photoshop, Illustrator, etc.)
- **Acrobat Pro DC**
- **Adobe Stock**
- **Adobe Express**
- **Adobe Firefly**
- **Frame.io**

## Troubleshooting

### "Invalid credentials" error

- Verify Client ID and Client Secret are correct
- Check that the Technical Account ID matches
- Ensure the OAuth credentials haven't expired

### "Forbidden" error

- The User Management API must be added to the project
- Verify the organization ID is correct
- Ensure admin permissions in Admin Console

### Missing users

- Check if users are provisioned through identity federation
- Verify the correct organization is selected
- Some users may be in separate product profiles
