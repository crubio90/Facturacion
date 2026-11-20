from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles, verify_internal_scraper_token
from app.core.config import get_settings
from app.core.database import get_db
from app.models.scrape_job import ScrapeJob, ScrapeStatus, ScrapeTriggerType
from app.models.user import User, UserRole
from app.schemas.scrape import (
    ScrapeJobRead,
    ScraperStatusRead,
    SyncIngestPayload,
    TriggerScrapeRequest,
)
from app.services.sync_service import ingest_scrape_payload

router = APIRouter(tags=["Webscraping y Sincronización"])


def _serialize_job(job: ScrapeJob) -> ScrapeJobRead:
    return ScrapeJobRead(
        id=job.id,
        trigger_type=job.trigger_type,
        mode=job.mode,
        status=job.status,
        triggered_by_name=job.triggered_by.full_name if job.triggered_by else "Scheduler Automático",
        started_at=job.started_at,
        finished_at=job.finished_at,
        clients_processed=job.clients_processed,
        invoices_created=job.invoices_created,
        invoices_updated=job.invoices_updated,
        overdue_detected=job.overdue_detected,
        log_summary=job.log_summary,
        error_message=job.error_message,
    )


@router.get("/scrape/status", response_model=ScraperStatusRead)
async def get_scraper_status(
    _: User = Depends(get_current_user),
) -> ScraperStatusRead:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
            resp = await client.get(
                f"{settings.SCRAPER_SERVICE_URL.rstrip('/')}/status",
                headers={"X-Internal-Token": settings.SCRAPER_INTERNAL_TOKEN},
            )
            resp.raise_for_status()
            data = resp.json()
            return ScraperStatusRead(
                reachable=True,
                mode=data.get("mode"),
                schedule_cron=data.get("schedule_cron"),
                timezone=data.get("timezone"),
                next_run_time=data.get("next_run_time"),
                is_running=bool(data.get("is_running", False)),
                detail=data.get("detail"),
            )
    except Exception as exc:
        return ScraperStatusRead(
            reachable=False,
            detail=f"No se pudo conectar con el contenedor scraper ({settings.SCRAPER_SERVICE_URL}): {exc}",
        )


@router.get("/scrape/jobs", response_model=list[ScrapeJobRead])
def list_scrape_jobs(
    limit: int = Query(default=30, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ScrapeJobRead]:
    jobs = db.scalars(
        select(ScrapeJob)
        .options(selectinload(ScrapeJob.triggered_by))
        .order_by(ScrapeJob.started_at.desc())
        .limit(limit)
    ).all()
    return [_serialize_job(j) for j in jobs]


@router.post("/scrape/trigger", response_model=ScrapeJobRead)
async def trigger_scrape_on_demand(
    payload: TriggerScrapeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.COBRANZA)),
) -> ScrapeJobRead:
    """Dispara una ejecución on-demand en el contenedor Docker de webscraping (facturacion.cl)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    job = ScrapeJob(
        trigger_type=ScrapeTriggerType.ON_DEMAND.value,
        mode=payload.mode or "default",
        status=ScrapeStatus.RUNNING.value,
        triggered_by_user_id=current_user.id,
        started_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            resp = await client.post(
                f"{settings.SCRAPER_SERVICE_URL.rstrip('/')}/scrape/run",
                json={
                    "job_id": job.id,
                    "trigger_type": ScrapeTriggerType.ON_DEMAND.value,
                    "mode": payload.mode,
                },
                headers={"X-Internal-Token": settings.SCRAPER_INTERNAL_TOKEN},
            )
            resp.raise_for_status()
    except Exception as exc:
        job.status = ScrapeStatus.FAILED.value
        job.finished_at = datetime.now(timezone.utc)
        job.error_message = f"No se pudo ejecutar el contenedor scraper: {exc}"
        db.commit()
        db.refresh(job)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=job.error_message,
        )

    db.expire_all()
    updated_job = db.scalar(
        select(ScrapeJob)
        .where(ScrapeJob.id == job.id)
        .options(selectinload(ScrapeJob.triggered_by))
    )
    return _serialize_job(updated_job or job)


@router.post("/internal/sync/ingest", response_model=ScrapeJobRead)
def ingest_from_scraper(
    payload: SyncIngestPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_scraper_token),
) -> ScrapeJobRead:
    """Endpoint interno consumido por el contenedor scraper (scheduler y on-demand)."""
    job = ingest_scrape_payload(db, payload)
    loaded = db.scalar(
        select(ScrapeJob)
        .where(ScrapeJob.id == job.id)
        .options(selectinload(ScrapeJob.triggered_by))
    )
    return _serialize_job(loaded or job)
