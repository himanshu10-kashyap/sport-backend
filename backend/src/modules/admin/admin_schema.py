from typing import List

from fastapi import UploadFile
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

    def clean_title(self) -> str:
        return self.title.strip()

    def clean_description(self) -> str | None:
        return (self.description or "").strip() or None


class AdvertisementUpdateSchema(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    file: UploadFile | None = None

    def clean_title(self) -> str | None:
        return self.title.strip() if self.title is not None else None

    def clean_description(self) -> str | None:
        return (self.description or "").strip() or None

    def has_new_file(self) -> bool:
        return self.file is not None and bool(self.file.filename)

