from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.client import Client, SaleRestrictionStatus
from app.models.invoice import InvoiceStatus
from app.models.reminder import PaymentReminder
from app.models.scrape_job import ScrapeJob
from app.models.user import User
from app.schemas.dashboard import DashboardMetrics
from app.schemas.scrape import ScrapeJobRead
from app.services.client_metrics import build_client_summary, refresh_invoice_status

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardMetrics:
    settings = get_settings()
    clients = list(
        db.scalars(select(Client).options(selectinload(Client.invoices))).all()
    )

    # Ensure overdue invoice statuses reflect current date
    dirty = False
    for c in clients:
        for inv in c.invoices:
            old_status = inv.status
            if refresh_invoice_status(inv) != old_status:
                dirty = True
    if dirty:
        db.commit()

    summaries = [build_client_summary(c, list(c.invoices)) for c in clients]

    total_por_cobrar = sum((s.total_por_cobrar for s in summaries), Decimal("0.00"))
    total_vencido = sum((s.total_vencido for s in summaries), Decimal("0.00"))
    total_pagado = sum((s.total_pagado for s in summaries), Decimal("0.00"))
    facturas_pendientes = sum(s.facturas_pendientes_count for s in summaries)
    facturas_vencidas = sum(s.facturas_vencidas_count for s in summaries)
    facturas_pagadas = sum(s.facturas_pagadas_count for s in summaries)

    clients_with_overdue = sum(1 for s in summaries if s.facturas_vencidas_count > 0)
    clients_sales_risk = sum(1 for s in summaries if s.is_sales_risk)
    clients_sale_restricted = sum(
        1
        for s in summaries
        if s.sale_restriction_status
        in (SaleRestrictionStatus.RESTRICTED.value, SaleRestrictionStatus.LIMITED.value)
    )

    since_30d = datetime.now(timezone.utc) - timedelta(days=30)
    reminders_sent_30d = (
        db.scalar(
            select(func.count(PaymentReminder.id)).where(
                PaymentReminder.sent_at >= since_30d
            )
        )
        or 0
    )

    last_job = db.scalar(
        select(ScrapeJob)
        .options(selectinload(ScrapeJob.triggered_by))
        .order_by(ScrapeJob.started_at.desc())
        .limit(1)
    )
    last_job_read = None
    if last_job:
        last_job_read = ScrapeJobRead(
            id=last_job.id,
            trigger_type=last_job.trigger_type,
            mode=last_job.mode,
            status=last_job.status,
            triggered_by_name=last_job.triggered_by.full_name if last_job.triggered_by else "Scheduler",
            started_at=last_job.started_at,
            finished_at=last_job.finished_at,
            clients_processed=last_job.clients_processed,
            invoices_created=last_job.invoices_created,
            invoices_updated=last_job.invoices_updated,
            overdue_detected=last_job.overdue_detected,
            log_summary=last_job.log_summary,
            error_message=last_job.error_message,
        )

    priority_clients = sorted(
        [s for s in summaries if s.is_sales_risk or s.facturas_vencidas_count > 0],
        key=lambda x: (not x.is_sales_risk, -x.total_vencido, -x.max_dias_mora),
    )[:8]

    return DashboardMetrics(
        total_clients=len(summaries),
        clients_with_overdue=clients_with_overdue,
        clients_sales_risk=clients_sales_risk,
        clients_sale_restricted=clients_sale_restricted,
        total_por_cobrar=total_por_cobrar,
        total_vencido=total_vencido,
        total_pagado=total_pagado,
        facturas_pendientes=facturas_pendientes,
        facturas_vencidas=facturas_vencidas,
        facturas_pagadas=facturas_pagadas,
        reminders_sent_30d=reminders_sent_30d,
        risk_reminder_threshold=settings.RISK_REMINDER_THRESHOLD,
        smtp_configured=settings.smtp_is_configured,
        smtp_dry_run=settings.SMTP_DRY_RUN,
        last_scrape_job=last_job_read,
        priority_clients=priority_clients,
    )
