from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScrapedInvoiceInput(BaseModel):
    external_id: str = Field(min_length=2, max_length=100)
    tipo_dte: str = "33"
    tipo_dte_nombre: str = "Factura Electrónica"
    folio: int
    fecha_emision: date
    fecha_vencimiento: date
    fecha_pago: date | None = None
    monto_neto: Decimal = Decimal("0.00")
    monto_iva: Decimal = Decimal("0.00")
    monto_total: Decimal
    monto_pagado: Decimal = Decimal("0.00")
    saldo_pendiente: Decimal | None = None
    status: str | None = None
    source_url: str | None = None
    raw_metadata: dict[str, Any] | None = None


class ScrapedClientInput(BaseModel):
    rut: str = Field(min_length=5, max_length=20)
    razon_social: str = Field(min_length=2, max_length=255)
    nombre_fantasia: str | None = None
    encargado_compras_nombre: str | None = None
    encargado_compras_email: str | None = None
    encargado_compras_telefono: str | None = None
    credito_limite: Decimal | None = None
    dias_credito: int | None = None
    invoices: list[ScrapedInvoiceInput] = Field(default_factory=list)


class SyncIngestPayload(BaseModel):
    job_id: int | None = None
    trigger_type: str = "SCHEDULED"
    mode: str = "mock"
    status: str = "SUCCESS"
    error_message: str | None = None
    log_summary: str | None = None
    clients: list[ScrapedClientInput] = Field(default_factory=list)


class TriggerScrapeRequest(BaseModel):
    mode: str | None = Field(default=None, pattern="^(mock|playwright)$")


class ScrapeJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trigger_type: str
    mode: str
    status: str
    triggered_by_name: str | None = None
    started_at: datetime
    finished_at: datetime | None
    clients_processed: int
    invoices_created: int
    invoices_updated: int
    overdue_detected: int
    log_summary: str | None
    error_message: str | None


class ScraperStatusRead(BaseModel):
    reachable: bool
    mode: str | None = None
    schedule_cron: str | None = None
    timezone: str | None = None
    next_run_time: str | None = None
    is_running: bool = False
    detail: str | None = None
