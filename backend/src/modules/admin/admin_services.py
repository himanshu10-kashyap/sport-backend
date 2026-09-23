import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.admin.admin_helper import (
    get_admin_by_username,
    hash_password,
    serialize_admin,
    verify_password,
)
from src.modules.admin.admin_schema import AdminLoginSchema, AdminRegisterSchema
from src.models.admin_model import Admin
from utils.common_schema import api_response_error, api_response_success
from utils.jwt import create_access_token
from utils.status_code import StatusCode

logger = logging.getLogger(__name__)

load_dotenv()


async def register_admin(db: AsyncSession, payload: AdminRegisterSchema):
    try:
        if await get_admin_by_username(db, payload.username):
            return api_response_error(
                "Username already exists", StatusCode.conflict, []
            )

        hashed_password = hash_password(payload.password)

        new_admin = Admin(
            username=payload.username,
            password=hashed_password,
            role="ADMIN",
            created_by=None,
            is_reset=True,
        )

        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)

        return api_response_success(
            serialize_admin(new_admin),
            "Admin registered successfully",
            StatusCode.create,
        )

    except Exception as e:
        await db.rollback()
        logger.exception("register_admin failed")
        return api_response_error(str(e), StatusCode.internalServerError, [])


async def login_admin(db: AsyncSession, payload: AdminLoginSchema):
    try:
        admin = await get_admin_by_username(db, payload.username)
        if not admin or not verify_password(payload.password, admin.password):
            return api_response_error(
                "Invalid username or password", StatusCode.unauthorized, []
            )

        if admin.status != "ACTIVE":
            return api_response_error(
                "Admin account is not active", StatusCode.forbidden, []
            )

        token = create_access_token(
            {"userid": str(admin.userid), "role": admin.role}
        )
        admin.token = token
        await db.commit()

        return api_response_success(
            {
                "access_token": token,
                "token_type": "bearer",
                "admin": serialize_admin(admin),
            },
            "Login successful",
            StatusCode.success,
        )

    except Exception as e:
        await db.rollback()
        logger.exception("login_admin failed")
        return api_response_error(str(e), StatusCode.internalServerError, [])