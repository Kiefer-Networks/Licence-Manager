#!/bin/sh
set -e

# Create data directories if they don't exist
# These directories are needed for file uploads (avatars, logos, etc.)
mkdir -p /app/data/admin_avatars
mkdir -p /app/data/avatars
mkdir -p /app/data/provider_logos
mkdir -p /app/data/files
mkdir -p /app/data/logos
mkdir -p /app/data/backups

# Execute the main command
exec "$@"
