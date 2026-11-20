from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.client import Client
from app.models.invoice import Invoice, InvoiceStatus
from app.models.reminder import PaymentReminder, ReminderStatus, ReminderTriggerType
from app.models.user import User
from app.schemas.reminder import PaymentReminderRead
from app.services.client_metrics import refresh_invoice_status
from app.services.email_service import send_reminder_email


def serialize_reminder(
    reminder: PaymentReminder,
    client: Client | None = None,
    marked_as_sales_risk: bool = False,
) -> PaymentReminderRead:
    c = client or reminder.client
    triggered_by_name = reminder.triggered_by.full_name if reminder.triggered_by else None
    return PaymentReminderRead(
        id=reminder.id,
        client_id=reminder.client_id,
        client_rut=c.rut if c else None,
        client_razon_social=c.razon_social if c else None,
        invoice_id=reminder.invoice_id,
        invoice_ids=reminder.invoice_ids or [],
        invoice_folios=reminder.invoice_folios or [],
        recipient_email=reminder.recipient_email,
        recipient_name=reminder.recipient_name,
        subject=reminder.subject,
        body_preview=reminder.body_preview,
        reminder_sequence=reminder.reminder_sequence,
        status=reminder.status,
        error_message=reminder.error_message,
        trigger_type=reminder.trigger_type,
        triggered_by_name=triggered_by_name,
        sent_at=reminder.sent_at,
        marked_as_sales_risk=marked_as_sales_risk,
    )


def dispatch_client_reminder(
    db: Session,
    client_id: int,
    invoice_id: int | None = None,
    override_email: str | None = None,
    custom_note: str | None = None,
    triggered_by: User | None = None,
    trigger_type: str = ReminderTriggerType.MANUAL.value,
) -> tuple[PaymentReminder, bool]:
    settings = get_settings()
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado.")

    recipient_email = override_email or client.encargado_compras_email
    if not recipient_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El cliente no tiene correo del encargado de compras registrado. Actualiza su ficha antes de enviar el recordatorio.",
        )

    stmt = select(Invoice).where(Invoice.client_id == client.id)
    if invoice_id is not None:
        stmt = stmt.where(Invoice.id == invoice_id)

    invoices = list(db.scalars(stmt).all())
    overdue_invoices: list[Invoice] = []
    for inv in invoices:
        refresh_invoice_status(inv)
        if inv.status == InvoiceStatus.VENCIDA.value and inv.saldo_pendiente > Decimal("0"):
            overdue_invoices.append(inv)

    if not overdue_invoices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existen facturas vencidas con saldo pendiente para enviar recordatorio.",
        )

    overdue_invoices.sort(key=lambda x: x.fecha_vencimiento)

    next_sequence = client.reminder_count + 1
    delivery = send_reminder_email(
        recipient_email=recipient_email,
        client=client,
        overdue_invoices=overdue_invoices,
        reminder_sequence=next_sequence,
        threshold=settings.RISK_REMINDER_THRESHOLD,
        custom_note=custom_note,
    )

    now = datetime.now(timezone.utc)
    reminder = PaymentReminder(
        client_id=client.id,
        invoice_id=overdue_invoices[0].id if len(overdue_invoices) == 1 else invoice_id,
        invoice_ids=[inv.id for inv in overdue_invoices],
        invoice_folios=[inv.folio for inv in overdue_invoices],
        recipient_email=recipient_email,
        recipient_name=client.encargado_compras_nombre,
        subject=delivery.subject,
        body_preview=delivery.text_body,
        reminder_sequence=next_sequence,
        status=delivery.status,
        error_message=delivery.error_message,
        trigger_type=trigger_type,
        triggered_by_user_id=triggered_by.id if triggered_by else None,
        sent_at=now,
    )
    db.add(reminder)

    newly_marked_risk = False
    if delivery.status in (ReminderStatus.SENT.value, ReminderStatus.DRY_RUN.value):
        client.reminder_count = next_sequence
        client.last_reminder_at = now

        if client.reminder_count >= settings.RISK_REMINDER_THRESHOLD and not client.is_sales_risk:
            client.is_sales_risk = True
            client.sales_risk_marked_at = now
            client.sales_risk_reason = (
                f"Alcanzó {client.reminder_count} recordatorios de pago enviados por facturas vencidas "
                f"(umbral configurado: {settings.RISK_REMINDER_THRESHOLD})."
            )
            newly_marked_risk = True

    db.commit()
    db.refresh(reminder)
    db.refresh(client)
    return reminder, newly_marked_risk
