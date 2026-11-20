import asyncio
import logging

import httpx

from app.config import ScraperSettings
from app.schemas import ScrapeExecutionResult
from app.scrapers.facturacion_cl import FacturacionClPlaywrightScraper
from app.scrapers.mock_scraper import MockFacturacionScraper

logger = logging.getLogger(__name__)


class ScrapeCoordinator:
    def __init__(self, settings: ScraperSettings) -> None:
        self.settings = settings
        self._lock = asyncio.Lock()
        self.is_running: bool = False

    async def execute_and_push(
        self,
        trigger_type: str = "SCHEDULED",
        mode: str | None = None,
        job_id: int | None = None,
    ) -> ScrapeExecutionResult:
        selected_mode = (mode or self.settings.SCRAPER_MODE).lower().strip()

        async with self._lock:
            self.is_running = True
            try:
                if selected_mode == "playwright":
                    scraper = FacturacionClPlaywrightScraper(self.settings)
                else:
                    selected_mode = "mock"
                    scraper = MockFacturacionScraper()

                logger.info(
                    "Iniciando extracción (%s) en modo=%s (job_id=%s)...",
                    trigger_type,
                    selected_mode,
                    job_id,
                )
                result = await scraper.run()
                await self._push_to_backend(
                    result=result,
                    trigger_type=trigger_type,
                    job_id=job_id,
                )
                return result
            finally:
                self.is_running = False

    async def _push_to_backend(
        self,
        result: ScrapeExecutionResult,
        trigger_type: str,
        job_id: int | None,
    ) -> None:
        url = f"{self.settings.BACKEND_API_URL.rstrip('/')}/api/v1/internal/sync/ingest"
        payload = {
            "job_id": job_id,
            "trigger_type": trigger_type,
            "mode": result.mode,
            "status": result.status,
            "error_message": result.error_message,
            "log_summary": result.log_summary,
            "clients": [c.model_dump(mode="json") for c in result.clients],
        }
        headers = {"X-Internal-Token": self.settings.SCRAPER_INTERNAL_TOKEN}

        async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("Datos sincronizados con backend exitosamente (%s).", resp.status_code)
