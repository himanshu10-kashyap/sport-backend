from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin_model import Admin
from src.models.permission_model import Permission
from src.models.rate_limit_model import RATE_LIMIT_DEFAULT_SECONDS, RateLimit

password_hasher = PasswordHasher()


async def get_admin_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(Admin).where(Admin.username == username))
    return result.scalars().first()


async def get_admin_by_id(db: AsyncSession, admin_id):
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    return result.scalars().first()


async def get_admin_by_userid(db: AsyncSession, userid: str):
    result = await db.execute(select(Admin).where(Admin.userid == userid))
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


async def get_permission_list(db: AsyncSession, admin_userid: str) -> list:
    result = await db.execute(
        select(Permission.permission).where(Permission.adminid == admin_userid)
    )
    return [p for p in result.scalars().all()]


async def get_rate_limit_value(db: AsyncSession) -> int:
    result = await db.execute(
        select(RateLimit.value).where(RateLimit.id == 1)
    )
    value = result.scalars().first()
    return int(value) if value is not None else RATE_LIMIT_DEFAULT_SECONDS


async def set_rate_limit_value(db: AsyncSession, value: int):
    existing = (
        await db.execute(select(RateLimit).where(RateLimit.id == 1))
    ).scalars().first()
    if existing:
        existing.value = value
    else:
        db.add(RateLimit(id=1, value=value))
    await db.commit()