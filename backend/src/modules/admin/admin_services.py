import logging
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.admin.admin_helper import (
    get_admin_by_userid,
    get_admin_by_username,
    get_permission_list,
    get_rate_limit_value,
    hash_password,
    serialize_admin,
    set_rate_limit_value,
    verify_password,
)
from src.modules.admin.admin_schema import (
    AdminLoginSchema,
    AdminRegisterSchema,
    CreateSubAdminSchema,
    SubAdminChangePasswordSchema,
    SubAdminResetPasswordSchema,
    UpdatePermissionSchema,
)
from src.models.admin_model import Admin
from src.models.permission_model import Permission
from utils.common_schema import (
    PaginationSchema,
    api_response_error,
    api_response_success,
)
from utils.jwt import create_access_token
from utils.status_code import StatusCode

logger = logging.getLogger(__name__)


async def register_admin(db: AsyncSession, payload: AdminRegisterSchema):
    try:
        if await db.scalar(select(func.count(Admin.id))):
            return api_response_error(
                "Admin registration is disabled", StatusCode.forbidden, []
            )

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
        await db.flush()
        db.add(Permission(userid=str(new_admin.userid), permission="ALL"))
        await db.commit()
        await db.refresh(new_admin)

        serializer_admin = serialize_admin(new_admin)
        permission_list = await get_permission_list(db, str(new_admin.userid))

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

        if admin.is_reset != True:
            return api_response_success(
                {"is_reset": admin.is_reset},
                "Reset your password",
                StatusCode.success,
            )

        if admin.status != "ACTIVE" or admin.is_deleted:
            return api_response_error(
                "Admin account is not active", StatusCode.forbidden, []
            )

        serializer_admin = serialize_admin(admin)
        permission_list = await get_permission_list(db, str(admin.userid))

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


async def create_sub_admin(
    db: AsyncSession, payload: CreateSubAdminSchema, current_user
):
    try:
        if await get_admin_by_username(db, payload.username):
            return api_response_error(
                "Username already exists", StatusCode.conflict, []
            )

        hashed_password = hash_password(payload.password)

        sub_admin = Admin(
            username=payload.username,
            password=hashed_password,
            role="SUBADMIN",
            created_by=current_user.userid,
        )

        db.add(sub_admin)
        await db.flush()

        if payload.permissions:
            permission_objects = [
                Permission(userid=str(sub_admin.userid), permission=perm)
                for perm in payload.permissions
            ]
            db.add_all(permission_objects)

        await db.commit()
        await db.refresh(sub_admin)

        return api_response_success(
            {
                "id": sub_admin.id,
                "userid": str(sub_admin.userid),
                "username": sub_admin.username,
                "role": sub_admin.role,
                "permissions": payload.permissions,
            },
            "Sub admin created successfully",
            StatusCode.create,
        )

    except Exception as e:
        await db.rollback()
        print("Error:", e)

        return api_response_error(str(e), StatusCode.internalServerError, [])


async def sub_admin_permissions_edit(
    db: AsyncSession, userid: str, payload: UpdatePermissionSchema, current_user
):
    try:
        sub_admin = await get_admin_by_userid(db, userid)
        if not sub_admin or sub_admin.role != "SUBADMIN":
            return api_response_error("Sub Admin not found", StatusCode.badRequest, [])

        if not payload.permissions:
            return api_response_error(
                "Permissions are required", StatusCode.badRequest, []
            )

        await db.execute(delete(Permission).where(Permission.userid == userid))

        permission_objects = [
            Permission(userid=userid, permission=permission)
            for permission in payload.permissions
        ]

        db.add_all(permission_objects)
        await db.commit()

        return api_response_success(
            {"userid": userid, "permissions": payload.permissions},
            "permissions updated successfully",
            StatusCode.success,
        )

    except Exception as e:
        await db.rollback()
        print("Error In Editing SubAdmin Permissions:", e)
        return api_response_error(str(e), StatusCode.internalServerError, [])


async def get_all_sub_admins(db: AsyncSession, pagination: PaginationSchema):
    try:
        page = pagination.page
        page_size = pagination.pageSize
        search = pagination.search

        query = (
            select(Admin)
            .where(
                Admin.role == "SUBADMIN",
                Admin.username.ilike(f"%{search}%"),
            )
            .order_by(Admin.created_at.desc())
        )

        total_items = (
            await db.execute(select(func.count()).select_from(query.subquery()))
        ).scalar() or 0

        if total_items == 0:
            return api_response_success(
                [],
                "No data found",
                StatusCode.success,
                {"page": page, "pageSize": page_size, "totalPages": 0, "totalItems": 0},
            )

        offset = (page - 1) * page_size

        sub_admins = (
            (await db.execute(query.offset(offset).limit(page_size)))
            .scalars()
            .all()
        )

        users = [
            {
                "id": str(admin.id),
                "userid": str(admin.userid),
                "username": admin.username,
                "role": admin.role,
            }
            for admin in sub_admins
        ]

        total_pages = (total_items + page_size - 1) // page_size

        pagination_data = {
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages,
            "totalItems": total_items,
        }

        return api_response_success(
            users,
            "Sub-admins fetched successfully",
            StatusCode.success,
            pagination_data,
        )

    except Exception as e:
        print("Error In Fetching Subadmins:", e)

        return api_response_error(str(e), StatusCode.internalServerError, [])


async def get_sub_admin_permission(
    db: AsyncSession, userid: str, current_user
):
    try:
        admin = await get_admin_by_userid(db, userid)

        if not admin or admin.role != "SUBADMIN":
            return api_response_error("Sub Admin not found", StatusCode.badRequest, [])

        if (
            current_user.role.upper() == "SUBADMIN"
            and str(admin.userid) != str(current_user.userid)
        ):
            return api_response_error(
                "Access denied: cannot view another subadmin's permissions",
                StatusCode.forbidden,
                [],
            )

        permissions_result = await db.execute(
            select(Permission.permission)
            .where(Permission.userid == userid)
            .order_by(Permission.id.desc())
        )

        permission_list = list(permissions_result.scalars().all())

        return api_response_success(
            {
                "userid": str(admin.userid),
                "id": str(admin.id),
                "username": admin.username,
                "role": admin.role,
                "permissions": permission_list,
            },
            (
                "Permissions retrieved successfully"
                if permission_list
                else "No permissions found"
            ),
            StatusCode.success,
        )

    except Exception as e:
        print("Error in get_sub_admin_permission:", e)
        return api_response_error()


async def sub_admin_change_password(db, payload, current_user):
    try:
        userid = payload.userid

        existing_admin = await get_admin_by_userid(db, userid)

        if not existing_admin or existing_admin.role != "SUBADMIN":
            return api_response_error(
                "Sub Admin not found!", StatusCode.badRequest, []
            )

        if payload.newPassword != payload.confirmPassword:
            return api_response_error(
                "New Password and Confirm Password do not match",
                StatusCode.badRequest,
                [],
            )

        password_matches_old = verify_password(
            payload.newPassword, existing_admin.password
        )

        if password_matches_old:
            return api_response_error(
                "New Password cannot be same as existing password",
                StatusCode.badRequest,
                [],
            )

        existing_admin.password = hash_password(payload.newPassword)
        existing_admin.is_reset = False

        await db.commit()
        await db.refresh(existing_admin)

        return api_response_success(
            [], "Password changed successfully!", StatusCode.success
        )

    except Exception as e:
        await db.rollback()
        return api_response_error(str(e), StatusCode.internalServerError, [])


async def sub_admin_reset_password(db: AsyncSession, payload):
    try:
        result = await db.execute(
            select(Admin).where(
                Admin.username == payload.username,
                Admin.role == "SUBADMIN",
                Admin.is_reset == False,
            )
        )

        existing_admin = result.scalars().first()

        if not existing_admin:
            return api_response_success([], "Admin not found!", StatusCode.success)

        if payload.newPassword != payload.confirmPassword:
            return api_response_error(
                "New Password and Confirm Password do not match",
                StatusCode.badRequest,
                [],
            )

        password_is_duplicate = verify_password(
            payload.newPassword, existing_admin.password
        )

        if password_is_duplicate:
            return api_response_error(
                "New Password Cannot Be The Same As Existing Password",
                StatusCode.badRequest,
                [],
            )

        hashed_password = hash_password(payload.newPassword)

        existing_admin.password = hashed_password
        existing_admin.is_reset = True

        await db.commit()
        await db.refresh(existing_admin)

        return api_response_success(
            [], "Password reset successful!", StatusCode.success
        )

    except Exception as e:
        await db.rollback()

        print("Error during admin password reset:", e)

        return api_response_error(str(e), StatusCode.internalServerError, [])


async def delete_sub_admin_service(db: AsyncSession, userid: str):
    try:
        sub_admin = await get_admin_by_userid(db, userid)
        if not sub_admin or sub_admin.role != "SUBADMIN":
            return api_response_error("SubAdmin not found", StatusCode.badRequest, [])

        await db.execute(delete(Permission).where(Permission.userid == userid))

        result = await db.execute(delete(Admin).where(Admin.userid == userid))

        if result.rowcount == 0:
            return api_response_error("SubAdmin not found", StatusCode.badRequest, [])

        await db.commit()

        return api_response_success(
            [], "SubAdmin with permission deleted successfully", StatusCode.success
        )

    except Exception as e:
        await db.rollback()

        print("Error in deleteSubAdmin:", e)

        return api_response_error(str(e), StatusCode.internalServerError, [])


async def get_rate_limit_setting(db: AsyncSession):
    try:
        value = await get_rate_limit_value(db)
        return api_response_success(
            {"value": value},
            "Rate limit fetched successfully",
            StatusCode.success,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("get_rate_limit_setting failed")
        return api_response_error(str(e), StatusCode.internalServerError, [])


async def update_rate_limit_setting(db: AsyncSession, value: int):
    try:
        if value < 1:
            return api_response_error(
                "value must be at least 1 second", StatusCode.badRequest, []
            )

        await set_rate_limit_value(db, value)

        return api_response_success(
            {"value": value},
            "Rate limit updated successfully",
            StatusCode.success,
        )
    except Exception as e:
        await db.rollback()
        logger.exception("update_rate_limit_setting failed")
        return api_response_error(str(e), StatusCode.internalServerError, [])
