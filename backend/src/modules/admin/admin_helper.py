from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin_model import Admin

password_hasher = PasswordHasher()


async def get_admin_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(Admin).where(Admin.username == username))
    return result.scalars().first()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, ValueError):
        return False


def serialize_admin(admin: Admin) -> dict:
    return {
        "id": admin.id,
        "username": admin.username,
        "role": admin.role,
        "status": admin.status,
        "userid": str(admin.userid),
    }