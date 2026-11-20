from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.risk_decision import RiskDecisionType


class ClientUpdate(BaseModel):
    nombre_fantasia: str | None = Field(default=None, max_length=255)
    encargado_compras_nombre: str | None = Field(default=None, max_length=180)
    encargado_compras_email: EmailStr | None = None
    encargado_compras_telefono: str | None = Field(default=None, max_length=50)
    credito_limite: Decimal | None = Field(default=None, ge=0)
    dias_credito: int | None = Field(default=None, ge=0, le=365)


class SaleRiskDecisionCreate(BaseModel):
    decision: RiskDecisionType
    order_reference: str | None = Field(default=None, max_length=100)
    order_amount: Decimal | None = Field(default=None, ge=0)
    reason: str = Field(min_length=3, max_length=1000)


class SaleRiskDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    user_id: int | None
    user_name: str | None = None
    decision: str
    order_reference: str | None
    order_amount: Decimal | None
    reason: str
    created_at: datetime


class ClientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rut: str
    razon_social: str
    nombre_fantasia: str | None
    encargado_compras_nombre: str | None
    encargado_compras_email: str | None
    encargado_compras_telefono: str | None
    credito_limite: Decimal
    dias_credito: int

    reminder_count: int
    last_reminder_at: datetime | None
    is_sales_risk: bool
    sales_risk_marked_at: datetime | None
    sales_risk_reason: str | None

    sale_restriction_status: str
    sale_restriction_note: str | None
    sale_restriction_updated_at: datetime | None
    last_synced_at: datetime | None

    # Computed financial metrics
    total_por_cobrar: Decimal = Decimal("0.00")
    total_vencido: Decimal = Decimal("0.00")
    total_pagado: Decimal = Decimal("0.00")
    facturas_pendientes_count: int = 0
    facturas_vencidas_count: int = 0
    facturas_pagadas_count: int = 0
    max_dias_mora: int = 0
