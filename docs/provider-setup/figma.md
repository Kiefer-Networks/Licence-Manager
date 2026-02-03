# Figma Integration Setup

Track Figma organization members using the SCIM API.

## Prerequisites

- **Figma Business or Enterprise plan** (SCIM is not available on Starter/Professional)
- Organization Admin access

## Important Note

Figma's REST API does not provide endpoints for listing organization or team members. The only way to retrieve user information is through the SCIM API, which requires a Business or Enterprise plan.

## Setup Steps

### 1. Generate SCIM Token

1. Log in to [Figma](https://www.figma.com/) as an **Organization Admin**
2. Go to **Admin Settings**
3. Navigate to **Login and provisioning** → **SCIM provisioning**
4. Click **Generate SCIM token**
5. Copy the token immediately - it cannot be viewed again

### 2. Get Tenant ID

1. In **Admin Settings**, go to **SAML SSO**
2. Your **Tenant ID** is displayed in the SCIM URL format: `https://www.figma.com/scim/v2/{tenant_id}`

### 3. Configure in License Management

In the Settings page, add Figma provider:

- **SCIM Token**: Your SCIM API token
- **Tenant ID**: Your organization's tenant ID

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | Figma user ID |
| Email | User's email (from userName or emails) |
| Display Name | User's display name |
| Seat Type | Full, Dev, Collab, or Viewer |
| Active | Whether the user is active |
| Department | User's department (if set) |
| Title | User's job title (if set) |
| Figma Admin | Whether user is an admin |

## License Types

Figma has different seat types that are mapped to license types:

| Seat Type | License Type |
|-----------|-------------|
| Full | Figma Full Seat |
| Dev | Figma Dev Mode |
| Collab | Figma Collaborator |
| View/Viewer | Figma Viewer |

**Note:** Seat type information (`roles`) is only available on **Figma Enterprise** plans. On Business plans, all users will be imported as "Figma Viewer" by default.

### Manual License Type Adjustment (Business Plan)

If you have a Figma Business plan (not Enterprise), the seat type cannot be automatically detected from the API. In this case:

1. Go to the Figma provider detail page
2. Click the menu (three dots) next to any user
3. Select "Change License Type"
4. Choose the correct license type from the dropdown

This allows you to manually track the correct seat type for each user for cost allocation purposes.

## Troubleshooting

### "Unauthorized" or 401 error

- Verify the SCIM token is correct and not expired
- Ensure you have Organization Admin access
- Check if SCIM provisioning is enabled in Admin Settings

### Empty user list

- Verify your Tenant ID is correct
- Ensure your organization has users provisioned via SCIM

### "SCIM not available" error

- SCIM requires Figma Business or Enterprise plan
- Starter and Professional plans do not support SCIM API

## API Reference

- SCIM Base URL: `https://www.figma.com/scim/v2/{tenant_id}`
- Authentication: Bearer token in Authorization header
- Documentation: [Figma SCIM API](https://developers.figma.com/docs/rest-api/scim/)
