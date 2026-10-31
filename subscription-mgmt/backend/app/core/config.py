from pydantic_settings import BaseSettings


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
    FRONTEND_URL: str = "http://localhost:5173"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()

