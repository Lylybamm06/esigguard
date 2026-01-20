from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "ESIG'Guard"
    ENV: str = os.getenv("ENV", "dev")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./esigguard.db")
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        case_sensitive = True


settings = Settings()