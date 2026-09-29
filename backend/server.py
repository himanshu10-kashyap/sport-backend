# backend/server.py

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from utils.redis import close_redis_client


load_dotenv(".env")
if os.getenv("NODE_ENV") == "production":
    load_dotenv(".env.production")

# Auto-create missing database tables on startup

@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await close_redis_client()


app = FastAPI(
    title="SCORE",
    version="1.0.0",
    lifespan=lifespan,
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
from src.modules.cricket.cricket_routes import router as cricket_router

app.include_router(admin_router)
app.include_router(cricket_router)

from utils.rate_limit import DynamicRateLimitMiddleware

app.add_middleware(DynamicRateLimitMiddleware)


if __name__ == "__main__":     
    
    uvicorn.run(
        "server:app",
        host="localhost",
        # host="0.0.0.0",
        port=int(os.getenv("PORT", "8001")),
        reload=os.getenv("NODE_ENV", "development") != "production"
    )