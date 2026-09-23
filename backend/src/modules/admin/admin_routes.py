from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.modules.admin.admin_schema import AdminLoginSchema, AdminRegisterSchema
from src.modules.admin.admin_services import login_admin, register_admin

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


