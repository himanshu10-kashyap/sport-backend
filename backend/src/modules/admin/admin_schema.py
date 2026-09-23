from typing import List

from pydantic import BaseModel, Field


class AdminRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class AdminLoginSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class CreateSubAdminSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)
    permissions: list[str] = Field(default_factory=list)


class UpdatePermissionSchema(BaseModel):
    permissions: List[str] = Field(..., min_length=1)



class SubAdminChangePasswordSchema(BaseModel):
    adminid: str
    newPassword: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)


class SubAdminResetPasswordSchema(BaseModel):
    username: str
    newPassword: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)


class RateLimitSchema(BaseModel):
    value: int = Field(..., ge=1)
