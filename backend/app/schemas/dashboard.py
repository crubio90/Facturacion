from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.client import ClientSummary, SaleRiskDecisionRead
from app.schemas.invoice import InvoiceRead
from app.schemas.reminder import PaymentReminderRead
from app.schemas.scrape import ScrapeJobRead


class DashboardMetrics(BaseModel):
    total_clients: int
    clients_with_overdue: int
    clients_sales_risk: int
    clients_sale_restricted: int
    total_por_cobrar: Decimal
    total_vencido: Decimal
    total_pagado: Decimal
    facturas_pendientes: int
    facturas_vencidas: int
    facturas_pagadas: int
    reminders_sent_30d: int
    risk_reminder_threshold: int
    smtp_configured: bool
    smtp_dry_run: bool
    last_scrape_job: ScrapeJobRead | None = None
    priority_clients: list[ClientSummary]


class ClientDetailResponse(BaseModel):
    client: ClientSummary
    invoices: list[InvoiceRead]
    reminders: list[PaymentReminderRead]
    risk_decisions: list[SaleRiskDecisionRead]


class SystemConfigSummary(BaseModel):
    company_name: str
    risk_reminder_threshold: int
    smtp_dry_run: bool
    smtp_host: str
    smtp_port: int
    smtp_from_email: str
    smtp_from_name: str
    smtp_use_tls: bool
    smtp_configured: bool
    scraper_service_url: str
    server_time: datetime
