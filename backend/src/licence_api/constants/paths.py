"""Central path constants for data directories.

All file storage paths are defined here to avoid duplication across modules.
"""

import os
from pathlib import Path

# Base data directory
# Use DATA_DIR env var if set (Docker), otherwise use relative path (local dev)
_ENV_DATA_DIR = os.environ.get("DATA_DIR")
if _ENV_DATA_DIR:
    DATA_DIR = Path(_ENV_DATA_DIR)
else:
    _PACKAGE_ROOT = Path(__file__).parent.parent.parent.parent
    DATA_DIR = _PACKAGE_ROOT / "data"

# Avatar directories
AVATAR_DIR = DATA_DIR / "avatars"
ADMIN_AVATAR_DIR = DATA_DIR / "admin_avatars"

# Provider-related directories
PROVIDER_LOGOS_DIR = DATA_DIR / "provider_logos"
PROVIDER_FILES_DIR = DATA_DIR / "files"

# Alias for backwards compatibility
FILES_DIR = PROVIDER_FILES_DIR
LOGOS_DIR = DATA_DIR / "logos"

# Backup directory
BACKUPS_DIR = DATA_DIR / "backups"
