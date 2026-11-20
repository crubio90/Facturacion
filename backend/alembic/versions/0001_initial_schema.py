"""Initial schema for DABERUSA Cobranza system

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-19 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("rut", sa.String(length=20), nullable=False),
        sa.Column("razon_social", sa.String(length=255), nullable=False),
        sa.Column("nombre_fantasia", sa.String(length=255), nullable=True),
        sa.Column("encargado_compras_nombre", sa.String(length=180), nullable=True),
        sa.Column("encargado_compras_email", sa.String(length=255), nullable=True),
        sa.Column("encargado_compras_telefono", sa.String(length=50), nullable=True),
        sa.Column("credito_limite", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("dias_credito", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("reminder_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reminder_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_sales_risk", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sales_risk_marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sales_risk_reason", sa.Text(), nullable=True),
        sa.Column("sale_restriction_status", sa.String(length=30), nullable=False, server_default="NONE"),
        sa.Column("sale_restriction_note", sa.Text(), nullable=True),
        sa.Column("sale_restriction_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sale_restriction_updated_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clients_id", "clients", ["id"])
    op.create_index("ix_clients_rut", "clients", ["rut"], unique=True)
    op.create_index("ix_clients_razon_social", "clients", ["razon_social"])
    op.create_index("ix_clients_is_sales_risk", "clients", ["is_sales_risk"])
    op.create_index("ix_clients_sale_restriction_status", "clients", ["sale_restriction_status"])

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=100), nullable=False),
        sa.Column("tipo_dte", sa.String(length=20), nullable=False, server_default="33"),
        sa.Column("tipo_dte_nombre", sa.String(length=100), nullable=False, server_default="Factura Electrónica"),
        sa.Column("folio", sa.Integer(), nullable=False),
        sa.Column("fecha_emision", sa.Date(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("fecha_pago", sa.Date(), nullable=True),
        sa.Column("monto_neto", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_iva", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("monto_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("monto_pagado", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("saldo_pendiente", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PENDIENTE"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("raw_metadata", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"])
    op.create_index("ix_invoices_client_id", "invoices", ["client_id"])
    op.create_index("ix_invoices_external_id", "invoices", ["external_id"], unique=True)
    op.create_index("ix_invoices_folio", "invoices", ["folio"])
    op.create_index("ix_invoices_fecha_vencimiento", "invoices", ["fecha_vencimiento"])
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "payment_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_ids", sa.JSON(), nullable=False),
        sa.Column("invoice_folios", sa.JSON(), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("recipient_name", sa.String(length=180), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("body_preview", sa.Text(), nullable=False),
        sa.Column("reminder_sequence", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False, server_default="MANUAL"),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_payment_reminders_id", "payment_reminders", ["id"])
    op.create_index("ix_payment_reminders_client_id", "payment_reminders", ["client_id"])
    op.create_index("ix_payment_reminders_invoice_id", "payment_reminders", ["invoice_id"])
    op.create_index("ix_payment_reminders_sent_at", "payment_reminders", ["sent_at"])

    op.create_table(
        "scrape_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clients_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoices_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invoices_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overdue_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("log_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_scrape_jobs_id", "scrape_jobs", ["id"])
    op.create_index("ix_scrape_jobs_status", "scrape_jobs", ["status"])
    op.create_index("ix_scrape_jobs_started_at", "scrape_jobs", ["started_at"])

    op.create_table(
        "sale_risk_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("order_reference", sa.String(length=100), nullable=True),
        sa.Column("order_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sale_risk_decisions_id", "sale_risk_decisions", ["id"])
    op.create_index("ix_sale_risk_decisions_client_id", "sale_risk_decisions", ["client_id"])
    op.create_index("ix_sale_risk_decisions_created_at", "sale_risk_decisions", ["created_at"])


def downgrade() -> None:
    op.drop_table("sale_risk_decisions")
    op.drop_table("scrape_jobs")
    op.drop_table("payment_reminders")
    op.drop_table("invoices")
    op.drop_table("clients")
    op.drop_table("users")
