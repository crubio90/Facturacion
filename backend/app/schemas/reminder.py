from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendReminderRequest(BaseModel):
    client_id: int
    invoice_id: int | None = None  # Si se omite, incluye todas las facturas vencidas del cliente
    override_email: EmailStr | None = None
    custom_note: str | None = Field(default=None, max_length=600)


class BulkReminderRequest(BaseModel):
    only_clients_with_email: bool = True
    exclude_already_risk: bool = False
    custom_note: str | None = Field(default=None, max_length=600)


class PaymentReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    client_rut: str | None = None
    client_razon_social: str | None = None
    invoice_id: int | None
    invoice_ids: list[int]
    invoice_folios: list[int]
    recipient_email: str
    recipient_name: str | None
    subject: str
    body_preview: str
    reminder_sequence: int
    status: str
    error_message: str | None
    trigger_type: str
    triggered_by_name: str | None = None
    sent_at: datetime
    marked_as_sales_risk: bool = False


class BulkReminderResult(BaseModel):
    total_targeted: int
    sent_count: int
    dry_run_count: int
    failed_count: int
    skipped_count: int
    newly_marked_risk_clients: list[str]
    reminders: list[PaymentReminderRead]
