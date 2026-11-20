from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "DABERUSA - Sistema de Cobranza"
    APP_VERSION: str = "1.0.0"
    COMPANY_NAME: str = "DABERUSA"

    # Database
    DATABASE_URL: str = "sqlite:///./daberusa_dev.db"

    # Auth / JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production-32chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    AUTO_SEED_DEMO_USERS: bool = True

    # Business rules
    RISK_REMINDER_THRESHOLD: int = 3

    # CORS
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:8080,http://localhost"

    # Scraper microservice
    SCRAPER_SERVICE_URL: str = "http://scraper:8001"
    SCRAPER_INTERNAL_TOKEN: str = "change-this-internal-scraper-token"

    # SMTP Email
    SMTP_DRY_RUN: bool = True
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_FROM_EMAIL: str = "cobranza@daberusa.cl"
    SMTP_FROM_NAME: str = "Cobranza DABERUSA"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def smtp_is_configured(self) -> bool:
        return bool(self.SMTP_HOST and not self.SMTP_DRY_RUN)


@lru_cache
def get_settings() -> Settings:
    return Settings()
