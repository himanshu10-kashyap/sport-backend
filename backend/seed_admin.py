import asyncio

from src.config.database import AsyncSessionLocal
from src.models.admin_model import Admin
from src.modules.admin.admin_helper import get_admin_by_username, hash_password


async def seed_admin() -> None:
    username = "admin"
    password = "123456"

    async with AsyncSessionLocal() as db:
        if await get_admin_by_username(db, username):
            print(f"Admin '{username}' already exists, skipping.")
            return

        admin = Admin(
            username=username,
            password=hash_password(password),
            role="ADMIN",
            created_by=None,
            is_reset=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)
        print(f"Admin '{username}' created (id={admin.id}).")


if __name__ == "__main__":
    asyncio.run(seed_admin())