# HiBob Integration Setup

HiBob serves as the HRIS (Human Resource Information System) source of truth for employee data.

## Prerequisites

- HiBob account with API access
- Admin or API access permissions

## Getting API Credentials

### 1. Create a Service User (Recommended)

1. Log in to HiBob as an admin
2. Go to **Settings** > **Integrations** > **Service Users**
3. Click **Add Service User**
4. Configure:
   - Name: "License Management Integration"
   - Permissions: Read access to People data
5. Save and copy the Service User ID

### 2. Generate API Token

1. Go to **Settings** > **Integrations** > **API**
2. Click **Generate new token**
3. Name: "License Management"
4. Copy the generated token (you won't be able to see it again)

## Configuration

In the License Management System setup wizard, enter:

- **API Key**: The generated API token
- **Service User ID**: (Optional) The service user ID

## Data Synced

The integration syncs the following employee data:

| Field | Description |
|-------|-------------|
| ID | HiBob employee ID |
| Email | Primary email address |
| Full Name | First and last name |
| Department | Department name |
| Status | Active or offboarded |
| Start Date | Employment start date |
| Termination Date | If offboarded |

## Sync Behavior

- **Frequency**: Hourly (configurable)
- **Method**: Full sync of all employees
- **Matching**: Employees are matched by HiBob ID

## Troubleshooting

### "Unauthorized" error

- Verify the API token is correct and not expired
- Check that the service user has the required permissions

### Missing employees

- Ensure the API token has access to all employees
- Check if employees are in specific sections that require additional permissions

### Outdated data

- Trigger a manual sync from the Settings page
- Check the last sync timestamp in the Providers list
