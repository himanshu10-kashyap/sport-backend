from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session



router = APIRouter(
    prefix="/api/user",
    tags=["cricket"]
)
