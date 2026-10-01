from typing import List

from fastapi import UploadFile
from pydantic import BaseModel, Field, field_validator

from src.models.advertisement_model import AdvertisementScreen, AdvertisementStatus
from src.modules.admin.admin_helper import (
    AVAILABLE_PERMISSIONS,
    normalize_permissions,
)

_ALLOWED_LOWER = {item.lower() for item in AVAILABLE_PERMISSIONS}


def _normalize_permission_list(value: list[str]) -> list[str]:
    invalid = [
        item
        for item in value
        if not isinstance(item, str) or item.strip().lower() not in _ALLOWED_LOWER
    ]

    if invalid:
        raise ValueError(
            f"Invalid permission(s): {', '.join(str(item) for item in invalid)}. "
            f"Allowed values: {', '.join(AVAILABLE_PERMISSIONS)}"
        )

    return normalize_permissions(value)


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

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, value: list[str]) -> list[str]:
        return _normalize_permission_list(value)


class UpdatePermissionSchema(BaseModel):
    permissions: List[str] = Field(..., min_length=1)

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, value: List[str]) -> List[str]:
        return _normalize_permission_list(value)



class SubAdminChangePasswordSchema(BaseModel):
    userid: str
    newPassword: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)


class SubAdminResetPasswordSchema(BaseModel):
    username: str
    newPassword: str = Field(..., min_length=6)
    confirmPassword: str = Field(..., min_length=6)


class RateLimitSchema(BaseModel):
    value: int = Field(..., ge=1)


class AdvertisementCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    file: UploadFile
    link: str | None = Field(None, max_length=500)
    screen: AdvertisementScreen
    status: AdvertisementStatus = AdvertisementStatus.ACTIVE

    def clean_title(self) -> str:
        return self.title.strip()

    def clean_description(self) -> str | None:
        return (self.description or "").strip() or None

    def clean_link(self) -> str | None:
        return (self.link or "").strip() or None


class AdvertisementUpdateSchema(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    file: UploadFile | None = None
    link: str | None = Field(None, max_length=500)
    screen: AdvertisementScreen | None = None
    status: AdvertisementStatus | None = None

    def clean_title(self) -> str | None:
        return self.title.strip() if self.title is not None else None

    def clean_description(self) -> str | None:
        return (self.description or "").strip() or None

    def clean_link(self) -> str | None:
        return (self.link or "").strip() or None

    def has_new_file(self) -> bool:
        return self.file is not None and bool(self.file.filename)

