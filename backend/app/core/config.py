"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    app_name: str = "JNTUA College Of Engineering Pulivendula Smart Exam Result Management System"
    environment: Literal["development", "testing", "production"] = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./exam.db"

    secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    refresh_cookie_name: str = "exam_refresh_token"

    institution_name: str = "JNTUA College Of Engineering Pulivendula"
    institution_address: str = "Pulivendula, Andhra Pradesh 516390"
    certificate_verification_base_url: str = "http://localhost:5173/verify"
    upload_dir: str = "./uploads"

    # Deployments without shell access can set AUTO_BOOTSTRAP=true. The app then
    # applies Alembic migrations and seeds institution data once at startup.
    auto_bootstrap: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
