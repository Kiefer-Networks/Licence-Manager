# Setting up Google OAuth

This guide explains how to set up Google OAuth 2.0 for the License Management System.

## Prerequisites

- A Google Cloud Platform account
- Access to create OAuth credentials

## Steps

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" and then "New Project"
3. Enter a project name (e.g., "License Management")
4. Click "Create"

### 2. Enable Required APIs

1. Go to "APIs & Services" > "Library"
2. Search for and enable the following APIs:
   - Google+ API (for basic profile info)
   - Admin SDK API (if using Google Workspace integration)

### 3. Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "Internal" (for organization users only) or "External"
3. Fill in the required fields:
   - App name: "License Management"
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. Add scopes:
   - `email`
   - `profile`
   - `openid`
6. Complete the setup

### 4. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Select "Web application"
4. Configure:
   - Name: "License Management Web Client"
   - Authorized JavaScript origins:
     - `http://localhost:3000` (development)
     - Your production URL
   - Authorized redirect URIs:
     - `http://localhost:3000/api/auth/callback/google` (development)
     - Your production callback URL
5. Click "Create"
6. Copy the **Client ID** and **Client Secret**

### 5. Update Environment Variables

Add the credentials to your `.env` file:

```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

## Optional: Restrict to Specific Domain

To restrict sign-in to users from a specific domain:

1. Set the `ALLOWED_EMAIL_DOMAIN` environment variable:

```env
ALLOWED_EMAIL_DOMAIN=yourcompany.com
```

2. Users with emails outside this domain will be rejected

## Troubleshooting

### "redirect_uri_mismatch" error

- Ensure the redirect URI in Google Console exactly matches your callback URL
- Check for trailing slashes
- Verify the protocol (http vs https)

### "access_denied" error

- Verify the OAuth consent screen is configured correctly
- Check if the user's email domain is allowed (if domain restriction is enabled)

### Token exchange failures

- Verify the Client ID and Client Secret are correct
- Ensure the credentials aren't expired or revoked
