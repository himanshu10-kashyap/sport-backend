from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
import os

from src.config.database import get_db
from src.models.admin_model import Admin
from src.models.permission_model import Permission

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM")

security = HTTPBearer()

ROLE_MODEL_MAP = {
    "ADMIN": Admin,
    "SUBADMIN": Admin,
}


def authorization(
    allowed_roles: list = None,
    required_permissions: list = None
):
    allowed_roles = allowed_roles or []
    required_permissions = required_permissions or []

    async def authorize_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ):
        try:
            token = credentials.credentials

            if not SECRET_KEY or not ALGORITHM:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="JWT configuration missing"
                )

            try:
                decoded = jwt.decode(
                    token,
                    SECRET_KEY,
                    algorithms=[ALGORITHM]
                )
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token"
                )

            user_id = decoded.get("id")
            role = (decoded.get("role") or "").upper()

            model = ROLE_MODEL_MAP.get(role)

            if not model:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid role"
                )

            result = await db.execute(
                select(model).where(model.id == user_id)
            )
            existing_user = result.scalars().first()

            if not existing_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            if allowed_roles:
                allowed = [r.upper() for r in allowed_roles]

                if role not in allowed:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: invalid role"
                    )

            # Permission check for Admin / SubAdmin
            permissions_data = (
                (
                    await db.execute(
                        select(Permission).where(
                            Permission.adminid == str(existing_user.userid)
                        )
                    )
                )
                .scalars()
                .all()
            )

            permissions = [
                (p.permission or "").upper()
                for p in permissions_data
            ]

            if "ALL" in permissions:
                return existing_user

            if required_permissions:
                if not all(
                    permission.upper() in permissions
                    for permission in required_permissions
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: insufficient permissions"
                    )

            return existing_user

        except HTTPException:
            raise

        except Exception as error:
            print("AUTH ERROR:", error)

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    return authorize_user