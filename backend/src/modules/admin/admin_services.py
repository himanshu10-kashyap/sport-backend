import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.admin.admin_helper import (
    get_admin_by_username,
    get_permission_list,
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

        serializer_admin = serialize_admin(new_admin)
        permission_list = await get_permission_list(db, new_admin.id)

        token = create_access_token(
            {
                "userid": str(new_admin.userid),
                "id": new_admin.id,
                "username": new_admin.username,
                "role": new_admin.role,
            }
        )
        new_admin.token = token
        await db.commit()

        return api_response_success(
            {
                "accessToken": token,
                **serializer_admin,
                "permissions": permission_list,
            },
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

        serializer_admin = serialize_admin(admin)
        permission_list = await get_permission_list(db, admin.id)

        token = create_access_token(
            {
                "userid": str(admin.userid),
                "id": admin.id,
                "username": admin.username,
                "role": admin.role,
            }
        )
        admin.token = token
        await db.commit()

        return api_response_success(
            {
                "accessToken": token,
                **serializer_admin,
                "permissions": permission_list,
            },
            "Login successful",
            StatusCode.success,
        )

    except Exception as e:
        await db.rollback()
        logger.exception("login_admin failed")
        return api_response_error(str(e), StatusCode.internalServerError, [])