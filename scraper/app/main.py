import asyncio
from contextlib import asynccontextmanager
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import Depends, FastAPI, Header, HTTPException, status

from app.config import get_scraper_settings
from app.coordinator import ScrapeCoordinator
from app.schemas import RunScrapeRequest, ScrapeExecutionResult

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_scraper_settings()
coordinator = ScrapeCoordinator(settings)
scheduler = AsyncIOScheduler(timezone=settings.SCRAPE_TIMEZONE)


async def _scheduled_job() -> None:
    try:
        await coordinator.execute_and_push(trigger_type="SCHEDULED")
    except Exception as exc:
        logger.exception("Error en ejecución programada del scraper: %s", exc)


async def _startup_initial_sync() -> None:
    await asyncio.sleep(3)
    try:
        await coordinator.execute_and_push(trigger_type="SCHEDULED")
    except Exception as exc:
        logger.warning("Sincronización inicial en startup falló (reintentará en cron): %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    trigger = CronTrigger.from_crontab(
        settings.SCRAPE_SCHEDULE_CRON,
        timezone=settings.SCRAPE_TIMEZONE,
    )
    scheduler.add_job(
        _scheduled_job,
        trigger=trigger,
        id="facturacion_cl_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler iniciado con cron='%s' (%s) en modo=%s",
        settings.SCRAPE_SCHEDULE_CRON,
        settings.SCRAPE_TIMEZONE,
        settings.SCRAPER_MODE,
    )

    startup_task = None
    if settings.SCRAPER_RUN_ON_STARTUP:
        startup_task = asyncio.create_task(_startup_initial_sync())

    yield

    if startup_task and not startup_task.done():
        startup_task.cancel()
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="DABERUSA Scraper facturacion.cl",
    version="1.0.0",
    lifespan=lifespan,
)


def verify_token(x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")) -> None:
    if not x_internal_token or x_internal_token != settings.SCRAPER_INTERNAL_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token interno inválido.",
        )


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "service": "daberusa-facturacion-scraper"}


@app.get("/status")
def get_status(_: None = Depends(verify_token)) -> dict:
    job = scheduler.get_job("facturacion_cl_sync")
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None
    return {
        "mode": settings.SCRAPER_MODE,
        "schedule_cron": settings.SCRAPE_SCHEDULE_CRON,
        "timezone": settings.SCRAPE_TIMEZONE,
        "next_run_time": next_run,
        "is_running": coordinator.is_running,
        "detail": "Contenedor scraper operativo (APScheduler + Playwright/Mock).",
    }


@app.post("/scrape/run", response_model=ScrapeExecutionResult)
async def trigger_scrape(
    payload: RunScrapeRequest,
    _: None = Depends(verify_token),
) -> ScrapeExecutionResult:
    try:
        return await coordinator.execute_and_push(
            trigger_type=payload.trigger_type,
            mode=payload.mode,
            job_id=payload.job_id,
        )
    except Exception as exc:
        logger.exception("Error ejecutando scraping on-demand: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ejecutando scraping: {exc}",
        )
