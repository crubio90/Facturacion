from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ScrapedInvoice(BaseModel):
    external_id: str
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


class ScrapedClient(BaseModel):
    rut: str
    razon_social: str
    nombre_fantasia: str | None = None
    encargado_compras_nombre: str | None = None
    encargado_compras_email: str | None = None
    encargado_compras_telefono: str | None = None
    credito_limite: Decimal | None = None
    dias_credito: int | None = None
    invoices: list[ScrapedInvoice] = Field(default_factory=list)


class ScrapeExecutionResult(BaseModel):
    mode: str
    status: str = "SUCCESS"
    log_summary: str
    error_message: str | None = None
    clients: list[ScrapedClient] = Field(default_factory=list)


class RunScrapeRequest(BaseModel):
    job_id: int | None = None
    trigger_type: str = "ON_DEMAND"
    mode: str | None = None
