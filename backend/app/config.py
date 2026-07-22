from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path


class Settings(BaseSettings):
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/callback"

    OPENAI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = ""
    REDIS_TOKEN: str = ""

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "https://ai-assistant-rho-blond.vercel.app"]
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def redis_connection_url(self) -> str:
        if self.REDIS_URL:
            host = self.REDIS_URL.replace("https://", "").replace("http://", "")
            if self.REDIS_TOKEN:
                return f"rediss://default:{self.REDIS_TOKEN}@{host}:6379"
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"


settings = Settings()
