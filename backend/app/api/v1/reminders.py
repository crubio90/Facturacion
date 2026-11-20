from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.client import Client
from app.models.invoice import InvoiceStatus
from app.models.reminder import PaymentReminder, ReminderStatus, ReminderTriggerType
from app.models.user import User, UserRole
from app.schemas.reminder import (
    BulkReminderRequest,
    BulkReminderResult,
    PaymentReminderRead,
    SendReminderRequest,
)
from app.services.client_metrics import refresh_invoice_status
from app.services.reminder_service import dispatch_client_reminder, serialize_reminder

router = APIRouter(prefix="/reminders", tags=["Recordatorios de Pago"])


@router.get("", response_model=list[PaymentReminderRead])
def list_reminders(
    client_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PaymentReminderRead]:
    stmt = (
        select(PaymentReminder)
        .options(
            selectinload(PaymentReminder.client),
            selectinload(PaymentReminder.triggered_by),
        )
        .order_by(PaymentReminder.sent_at.desc())
        .limit(limit)
    )
    if client_id is not None:
        stmt = stmt.where(PaymentReminder.client_id == client_id)

    reminders = db.scalars(stmt).all()
    return [serialize_reminder(r, r.client) for r in reminders]


@router.post("/send", response_model=PaymentReminderRead)
def send_reminder(
    payload: SendReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.COBRANZA)),
) -> PaymentReminderRead:
    reminder, newly_marked_risk = dispatch_client_reminder(
        db=db,
        client_id=payload.client_id,
        invoice_id=payload.invoice_id,
        override_email=payload.override_email,
        custom_note=payload.custom_note,
        triggered_by=current_user,
        trigger_type=ReminderTriggerType.MANUAL.value,
    )
    return serialize_reminder(reminder, reminder.client, marked_as_sales_risk=newly_marked_risk)


@router.post("/send-bulk", response_model=BulkReminderResult)
def send_bulk_overdue_reminders(
    payload: BulkReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.COBRANZA)),
) -> BulkReminderResult:
    clients = list(
        db.scalars(select(Client).options(selectinload(Client.invoices))).all()
    )

    targeted_clients: list[Client] = []
    for c in clients:
        has_overdue = False
        for inv in c.invoices:
            refresh_invoice_status(inv)
            if inv.status == InvoiceStatus.VENCIDA.value and inv.saldo_pendiente > 0:
                has_overdue = True
        if not has_overdue:
            continue
        if payload.exclude_already_risk and c.is_sales_risk:
            continue
        targeted_clients.append(c)
    db.commit()

    sent_count = 0
    dry_run_count = 0
    failed_count = 0
    skipped_count = 0
    newly_marked: list[str] = []
    created_reminders: list[PaymentReminderRead] = []

    for c in targeted_clients:
        if not c.encargado_compras_email:
            skipped_count += 1
            continue
        try:
            rem, newly_risk = dispatch_client_reminder(
                db=db,
                client_id=c.id,
                custom_note=payload.custom_note,
                triggered_by=current_user,
                trigger_type=ReminderTriggerType.MANUAL.value,
            )
            if rem.status == ReminderStatus.SENT.value:
                sent_count += 1
            elif rem.status == ReminderStatus.DRY_RUN.value:
                dry_run_count += 1
            else:
                failed_count += 1
            if newly_risk:
                newly_marked.append(c.razon_social)
            created_reminders.append(
                serialize_reminder(rem, c, marked_as_sales_risk=newly_risk)
            )
        except HTTPException:
            skipped_count += 1

    return BulkReminderResult(
        total_targeted=len(targeted_clients),
        sent_count=sent_count,
        dry_run_count=dry_run_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        newly_marked_risk_clients=newly_marked,
        reminders=created_reminders,
    )
