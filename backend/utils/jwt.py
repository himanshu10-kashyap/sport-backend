from jose import jwt, JWTError, ExpiredSignatureError
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Optional
import os

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from src.config.database import get_db

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS   = 30

# auto_error=False so we handle missing token with a clear message ourselves
security = HTTPBearer(auto_error=False)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire    = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
