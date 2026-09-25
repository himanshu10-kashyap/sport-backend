from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.modules.admin.admin_schema import (
    AdminLoginSchema,
    AdminRegisterSchema,
    CreateSubAdminSchema,
    RateLimitSchema,
    SubAdminChangePasswordSchema,
    SubAdminResetPasswordSchema,
    UpdatePermissionSchema,
)
from src.modules.admin.admin_services import (
    create_sub_admin,
    delete_sub_admin_service,
    get_all_sub_admins,
    get_rate_limit_setting,
    get_sub_admin_permission,
    login_admin,
    register_admin,
    sub_admin_change_password,
    sub_admin_permissions_edit,
    sub_admin_reset_password,
    update_rate_limit_setting,
)
from middleware.auth import authorization
from utils.common_schema import PaginationSchema

router = APIRouter(
    prefix="/api/admin",
    tags=["Score Admin"],
)


@router.post("/register")
async def admin_register(
    payload: AdminRegisterSchema, db: AsyncSession = Depends(get_db)
):
    return await register_admin(db, payload)


@router.post("/login")
async def admin_login(payload: AdminLoginSchema, db: AsyncSession = Depends(get_db)):
    return await login_admin(db, payload)


@router.post("/subadmins")
async def create_subadmin(
    payload: CreateSubAdminSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await create_sub_admin(db, payload, current_user)


@router.put("/subadmins/{userid}/permissions")
async def edit_sub_admin_permissions(
    userid: str,
    payload: UpdatePermissionSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await sub_admin_permissions_edit(db, userid, payload, current_user)


@router.get("/subadmins")
async def fetch_all_sub_admins(
    pagination: PaginationSchema = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await get_all_sub_admins(db=db, pagination=pagination)


@router.get("/subadmins/{userid}/permissions")
async def fetch_sub_admin_permission(
    userid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await get_sub_admin_permission(db, userid)


@router.put("/subadmins/password/change")
async def change_sub_admin_password(
    payload: SubAdminChangePasswordSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await sub_admin_change_password(db, payload, current_user)


@router.put("/subadmins/password/reset")
async def sub_admin_reset_password_route(
    payload: SubAdminResetPasswordSchema,
    db: AsyncSession = Depends(get_db),
):
    return await sub_admin_reset_password(db, payload)


@router.delete("/subadmins/{userid}")
async def delete_sub_admin(
    userid: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(authorization(allowed_roles=["ADMIN"])),
):
    return await delete_sub_admin_service(db, userid)


@router.get("/settings/rate/limit")
async def fetch_rate_limit(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        authorization(
            allowed_roles=["ADMIN", "SUBADMIN"],
            required_permissions=["rate_limit"],
        )
    ),
):
    return await get_rate_limit_setting(db)


@router.put("/settings/rate/limit")
async def edit_rate_limit(
    payload: RateLimitSchema,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(
        authorization(
            allowed_roles=["ADMIN", "SUBADMIN"],
            required_permissions=["rate_limit"],
        )
    ),
):
    return await update_rate_limit_setting(db, payload.value)
