from typing import Any

from pydantic import BaseModel


class CricketResponseSchema(BaseModel):
    data: Any = None
    success: bool = True
    status_code: int = 200
    message: str = "Success"
    pagination: Any = None


class CricketErrorSchema(CricketResponseSchema):
    success: bool = False
