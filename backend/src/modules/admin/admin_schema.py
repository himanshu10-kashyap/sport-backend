from pydantic import BaseModel, Field


class AdminRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)


class AdminLoginSchema(BaseModel):
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)