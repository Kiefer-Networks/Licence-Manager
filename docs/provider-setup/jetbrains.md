# JetBrains Integration Setup

Track JetBrains IDE licenses (IntelliJ, PyCharm, WebStorm, etc.) in your organization.

## Prerequisites

- JetBrains Account with organization access
- License server or JetBrains Account subscription
- Customer Code

## Setup Steps

### 1. Get Customer Code

1. Log in to [JetBrains Account](https://account.jetbrains.com/)
2. Go to your organization/team
3. Navigate to **Licenses** or **Subscriptions**
4. Find your **Customer Code** (format: `XXXXXX-XXXXXX`)

### 2. Generate API Key

1. In JetBrains Account, go to **Settings**
2. Navigate to **API tokens** or **Access tokens**
3. Click **Generate new token**
4. Name: "License Management"
5. Select read permissions for licenses
6. Copy the API key

### 3. Configure in License Management

In the Settings page, add JetBrains provider:

- **API Key**: Your JetBrains API key
- **Customer Code**: Your customer/organization code

## Data Synced

| Field | Description |
|-------|-------------|
| User ID | JetBrains user ID |
| Email | User's email address |
| Name | User's full name |
| Licenses | Assigned product licenses |
| Product | IDE name (IntelliJ, PyCharm, etc.) |
| License Type | Personal, Commercial, or Academic |
| Expiry | License expiration date |

## License Types

JetBrains licenses include:

- **All Products Pack**: Access to all IDEs
- **IntelliJ IDEA Ultimate**
- **PyCharm Professional**
- **WebStorm**
- **PhpStorm**
- **Rider**
- **GoLand**
- **DataGrip**
- **RubyMine**
- **CLion**
- **DataSpell**
- **Aqua**
- **RustRover**

## Troubleshooting

### "401 Unauthorized" error

- Verify the API key is correct
- Check that the token hasn't expired
- Ensure read permissions are granted

### "Invalid customer code" error

- Verify the customer code format
- Ensure you have access to the organization
- Check for typos (case-sensitive)

### Missing licenses

- Ensure users have activated their licenses
- Check license assignment in JetBrains Account
- Verify the correct customer code is used
