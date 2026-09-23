# backend/server.py

import os
import sys
import subprocess


from dotenv import load_dotenv

# Load Environment
load_dotenv(".env")

if os.getenv("NODE_ENV") == "production":
    load_dotenv(".env.production")


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import uvicorn

# Auto-create missing database tables on startup

app = FastAPI(
    title="SCORE",
    version="1.0.0",
)


allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_URI", "").split(",")
    if origin.strip()
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

from src.modules.admin.admin_routes import router as admin_router

app.include_router(admin_router)

from utils.rate_limit import DynamicRateLimitMiddleware

app.add_middleware(DynamicRateLimitMiddleware)


if __name__ == "__main__":     
    
    uvicorn.run(
        "server:app",
        host="localhost",
        # host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=os.getenv("NODE_ENV") != "production"
    )