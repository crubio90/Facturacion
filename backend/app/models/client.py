import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SaleRestrictionStatus(str, enum.Enum):
    NONE = "NONE"                  # Venta habilitada normalmente
    LIMITED = "LIMITED"            # Venta limitada (ej. solo contado / cupo reducido)
    RESTRICTED = "RESTRICTED"      # Venta restringida / bloqueada por riesgo


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    rut: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    razon_social: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nombre_fantasia: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Contacto de compras (destinatario de recordatorios de pago)
    encargado_compras_nombre: Mapped[str | None] = mapped_column(String(180), nullable=True)
    encargado_compras_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    encargado_compras_telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Condiciones comerciales
    credito_limite: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"), nullable=False)
    dias_credito: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    # Estado de cobranza y Riesgo de Venta (al 3er recordatorio)
    reminder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_sales_risk: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    sales_risk_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sales_risk_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Control de restricción de venta a demanda del vendedor
    sale_restriction_status: Mapped[str] = mapped_column(
        String(30),
        default=SaleRestrictionStatus.NONE.value,
        index=True,
        nullable=False,
    )
    sale_restriction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sale_restriction_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sale_restriction_updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

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

    invoices = relationship("Invoice", back_populates="client", cascade="all, delete-orphan")
    reminders = relationship("PaymentReminder", back_populates="client", cascade="all, delete-orphan")
    risk_decisions = relationship("SaleRiskDecision", back_populates="client", cascade="all, delete-orphan")
    restriction_updated_by = relationship("User", foreign_keys=[sale_restriction_updated_by_id])
