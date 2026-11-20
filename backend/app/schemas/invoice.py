from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    client_rut: str | None = None
    client_razon_social: str | None = None
    client_is_sales_risk: bool = False
    external_id: str
    tipo_dte: str
    tipo_dte_nombre: str
    folio: int
    fecha_emision: date
    fecha_vencimiento: date
    fecha_pago: date | None
    monto_neto: Decimal
    monto_iva: Decimal
    monto_total: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    status: str
    dias_mora: int = 0
    source_url: str | None
    last_synced_at: datetime | None
