from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SPORTS_API_KEY: str
    SPORTS_API_BASE_URL: str
    API_RATE_LIMIT_SECONDS: int = 2
    REDIS_URL: str
    ENV: str = "development"
    APP_NAME: str = "Cricket Live Score API"

    class Config:
        env_file = ".env"

settings = Settings()