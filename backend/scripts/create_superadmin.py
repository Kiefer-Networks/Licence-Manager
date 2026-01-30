#!/usr/bin/env python
"""Create a superadmin user."""

import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from licence_api.config import get_settings
from licence_api.security.password import get_password_service


async def create_superadmin(email: str, password: str, name: str | None = None):
    """Create a superadmin user."""
    settings = get_settings()
    # Convert PostgresDsn to string and ensure it uses async driver
    db_url = str(settings.database_url).replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    password_service = get_password_service()

    # Validate password
    is_valid, errors = password_service.validate_password_strength(password)
    if not is_valid:
        print(f"Password validation failed: {errors}")
        return False

    # Hash password
    password_hash = password_service.hash_password(password)

    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(
            text("SELECT id FROM admin_users WHERE email = :email"),
            {"email": email.lower()}
        )
        existing = result.fetchone()
        if existing:
            print(f"User {email} already exists")
            return False

        # Get superadmin role
        result = await session.execute(
            text("SELECT id FROM roles WHERE code = 'superadmin'")
        )
        role = result.fetchone()
        if not role:
            print("Superadmin role not found. Run migrations first.")
            return False
        role_id = role[0]

        # Create user
        result = await session.execute(
            text("""
                INSERT INTO admin_users (id, email, name, password_hash, auth_provider, is_active)
                VALUES (gen_random_uuid(), :email, :name, :password_hash, 'local', true)
                RETURNING id
            """),
            {"email": email.lower(), "name": name, "password_hash": password_hash}
        )
        user_id = result.fetchone()[0]

        # Assign superadmin role
        await session.execute(
            text("""
                INSERT INTO user_roles (user_id, role_id)
                VALUES (:user_id, :role_id)
            """),
            {"user_id": user_id, "role_id": role_id}
        )

        await session.commit()
        print(f"Superadmin user created: {email}")
        return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a superadmin user")
    parser.add_argument("--email", required=True, help="Email address")
    parser.add_argument("--password", required=True, help="Password (min 12 chars)")
    parser.add_argument("--name", help="Display name")
    args = parser.parse_args()

    asyncio.run(create_superadmin(args.email, args.password, args.name))
