"""Seed database with initial roles and admin user.
Run: python scripts/seed.py (from backend directory)

The admin password is read from the ADMIN_PASSWORD env var (default: admin123456).
"""

import asyncio
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session, engine
from app.core.security import hash_password
from app.models.role_menu import RoleMenu
from app.models.user import Base, Role, User

# Must match frontend's defaultRoleMenuMap
DEFAULT_ROLE_MENUS: dict[str, list[str]] = {
    "admin": [
        "/", "/models", "/settings", "/tools", "/mcp", "/knowledge",
        "/consultations", "/users", "/profile", "/permissions",
    ],
    "lawyer": [
        "/", "/models", "/settings", "/knowledge", "/consultations", "/profile",
    ],
    "user": [
        "/", "/consultations", "/profile",
    ],
}


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Roles
        roles_data = [
            ("user", "普通用户"),
            ("lawyer", "法律专家"),
            ("admin", "管理员"),
        ]
        for name, desc in roles_data:
            existing = await db.execute(select(Role).where(Role.name == name))
            if not existing.scalar_one_or_none():
                db.add(Role(name=name, description=desc))
        await db.commit()

        # Re-fetch roles with IDs
        role_rows = await db.execute(select(Role))
        role_map = {r.name: r for r in role_rows.scalars().all()}

        # Admin user
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123456")
        result = await db.execute(select(User).where(User.email == "admin@legalbot.com"))
        if not result.scalar_one_or_none():
            db.add(User(
                id=uuid.uuid4(),
                email="admin@legalbot.com",
                display_name="管理员",
                hashed_password=hash_password(admin_password),
                role_id=role_map["admin"].id,
            ))
            await db.commit()
            print("Admin user created successfully.")

        # Seed default role_menus for any role that has no entries
        for name, role in role_map.items():
            existing_menus = await db.execute(
                select(RoleMenu).where(RoleMenu.role_id == role.id).limit(1)
            )
            if existing_menus.first() is None:
                menus = DEFAULT_ROLE_MENUS.get(name, DEFAULT_ROLE_MENUS["user"])
                for key in menus:
                    db.add(RoleMenu(role_id=role.id, menu_key=key, enabled=True))
                print(f"Seeded {len(menus)} menu keys for role '{name}'")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
