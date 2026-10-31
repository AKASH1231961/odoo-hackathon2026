from pydantic import model_validator
from pydantic_settings import BaseSettings

INSECURE_SECRET_KEYS = {
    "change-me-in-production-please",
    "change-me-in-production-please-use-64-char-hex",
}


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/subscription_db"
    REDIS_URL: str = "redis://redis:6379/0"
    SECRET_KEY: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SMTP_HOST: str = "smtp.mailtrap.io"
    SMTP_PORT: int = 2525
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "billing@brightloop.test"
    FRONTEND_URL: str = "http://localhost:8081"
    # Comma-separated browser origins allowed to call the API, on top of FRONTEND_URL
    CORS_ORIGINS: str = "http://localhost:8081"
    ENVIRONMENT: str = "development"
    # First admin, created on start-up when the database has none
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    SEED_DEMO_DATA: bool = False
    LOGIN_MAX_FAILURES: int = 10
    LOGIN_LOCKOUT_SECONDS: int = 900

    @model_validator(mode="after")
    def refuse_public_secret_in_production(self):
        if self.ENVIRONMENT != "development" and self.SECRET_KEY in INSECURE_SECRET_KEYS:
            raise ValueError("SECRET_KEY must be changed outside development")
        return self

    @property
    def cors_origins(self) -> list:
        extra = [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return list(dict.fromkeys([self.FRONTEND_URL, *extra]))

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

