from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ScraperSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BACKEND_API_URL: str = "http://backend:8000"
    SCRAPER_INTERNAL_TOKEN: str = "change-this-internal-scraper-token"

    # Execution mode: "mock" | "playwright"
    SCRAPER_MODE: str = "mock"
    SCRAPE_SCHEDULE_CRON: str = "30 8,14 * * 1-5"
    SCRAPE_TIMEZONE: str = "America/Santiago"
    SCRAPER_RUN_ON_STARTUP: bool = True

    # facturacion.cl credentials & settings
    FACTURACION_BASE_URL: str = "https://www.facturacion.cl"
    FACTURACION_SYSTEM_SLUG: str = "daberusa"
    FACTURACION_USERNAME: str = ""
    FACTURACION_PASSWORD: str = ""
    FACTURACION_HEADLESS: bool = True
    FACTURACION_TIMEOUT_MS: int = 30000
    FACTURACION_SELECTORS_PATH: str = "/app/selectors.json"
    DEBUG_SCREENSHOTS_DIR: str = "/app/debug_screenshots"

    def resolve_selectors_file(self) -> Path:
        custom = Path(self.FACTURACION_SELECTORS_PATH)
        if custom.exists():
            return custom
        local_custom = Path(__file__).resolve().parents[1] / "selectors.json"
        if local_custom.exists():
            return local_custom
        return Path(__file__).resolve().parents[1] / "selectors.example.json"


@lru_cache
def get_scraper_settings() -> ScraperSettings:
    return ScraperSettings()
