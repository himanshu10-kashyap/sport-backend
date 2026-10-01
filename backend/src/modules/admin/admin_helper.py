from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.admin_model import Admin
from src.models.permission_model import Permission
from src.models.rate_limit_model import RATE_LIMIT_DEFAULT_SECONDS, RateLimit

password_hasher = PasswordHasher()

PERMISSION_ALL = "ALL"

SPECIFIC_PERMISSIONS = ("rate_limit", "advertisement")

AVAILABLE_PERMISSIONS = (PERMISSION_ALL, *SPECIFIC_PERMISSIONS)

_CANONICAL_BY_LOWER = {item.lower(): item for item in AVAILABLE_PERMISSIONS}


def normalize_permissions(values) -> list[str]:
    """Effective permission list for the given raw values.

    "ALL" is exclusive: if present the result is only ["ALL"], so a sub-admin
    handed "all" never also shows up as holding individual permissions.
    Unknown values are dropped, duplicates collapsed and order canonical.
    """
    cleaned: list[str] = []

    for value in values or []:
        canonical = _CANONICAL_BY_LOWER.get(
            value.strip().lower() if isinstance(value, str) else ""
        )
        if canonical is None or canonical in cleaned:
            continue
        cleaned.append(canonical)

    if PERMISSION_ALL in cleaned:
        return [PERMISSION_ALL]

    return [item for item in AVAILABLE_PERMISSIONS if item in cleaned]


def resolve_permissions(role, stored_permissions) -> list[str]:
    """Effective permissions for a holder of `role`.

    ADMIN always resolves to ["ALL"], so an admin login payload can never
    report individual permissions like "advertisement". Every other role
    reports exactly what was granted, with "ALL" still meaning everything.
    """
    if (role or "").strip().upper() == "ADMIN":
        return [PERMISSION_ALL]

    return normalize_permissions(stored_permissions)


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


async def get_permission_list(
    db: AsyncSession, userid: str, role: str | None = None
) -> list:
    result = await db.execute(
        select(Permission.permission).where(Permission.userid == userid)
    )
    return resolve_permissions(role, result.scalars().all())


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