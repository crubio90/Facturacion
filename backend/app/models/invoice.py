import enum
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InvoiceStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    VENCIDA = "VENCIDA"
    PAGADA = "PAGADA"
    ANULADA = "ANULADA"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    tipo_dte: Mapped[str] = mapped_column(String(20), default="33", nullable=False)
    tipo_dte_nombre: Mapped[str] = mapped_column(String(100), default="Factura Electrónica", nullable=False)
    folio: Mapped[int] = mapped_column(Integer, index=True, nullable=False)

    fecha_emision: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    fecha_pago: Mapped[date | None] = mapped_column(Date, nullable=True)

    monto_neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    monto_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    monto_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    saldo_pendiente: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        default=InvoiceStatus.PENDIENTE.value,
        index=True,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    client = relationship("Client", back_populates="invoices")
    reminders = relationship("PaymentReminder", back_populates="invoice")
