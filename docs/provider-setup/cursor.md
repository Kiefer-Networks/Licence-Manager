# Cursor Integration Setup

Track Cursor IDE team licenses.

## Overview

Cursor may not have a public API for team management at this time. This integration supports:

1. **API Integration** (when available)
2. **Manual CSV Import** (fallback)

## Option 1: API Integration

If Cursor provides a team API:

### 1. Get API Credentials

1. Contact Cursor support or check their API documentation
2. Obtain API key and team ID

### 2. Configure in License Management

In the Settings page, add Cursor provider:

- **API Key**: Your Cursor API key
- **Team ID**: Your team identifier

## Option 2: Manual CSV Import

For manual tracking without an API:

### 1. Export Team Members

Export your Cursor team members to a CSV file with the following format:

```csv
email,name,plan
user@example.com,John Doe,Pro
another@example.com,Jane Smith,Pro
```

### 2. Configure with Manual Data

In the provider configuration, provide the data as a JSON array:

```json
{
  "manual_data": [
    {"email": "user@example.com", "name": "John Doe", "plan": "Pro"},
    {"email": "another@example.com", "name": "Jane Smith", "plan": "Pro"}
  ]
}
```

## Data Synced

| Field | Description |
|-------|-------------|
| Email | User's email (used as ID) |
| Name | User's name |
| Plan | License plan (Pro, etc.) |
| Cost | Default: $20/month |

## Updating Manual Data

To update manually tracked licenses:

1. Go to **Settings** > **Providers**
2. Edit the Cursor provider
3. Update the manual_data JSON
4. Save and trigger a sync

## Troubleshooting

### API not available

- Use manual CSV import as a fallback
- Check Cursor documentation for API availability

### Matching issues

- Ensure email addresses match HiBob employee emails exactly
- Use lowercase for all email addresses
