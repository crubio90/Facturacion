import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RiskDecisionType(str, enum.Enum):
    RESTRICT_SALE = "RESTRICT_SALE"        # Bloquear venta al cliente en riesgo
    LIMIT_SALE = "LIMIT_SALE"              # Limitar venta (ej. solo pago contado / cupo acotado)
    ALLOW_EXCEPTION = "ALLOW_EXCEPTION"    # Autorizar pedido puntual pese a riesgo
    CLEAR_RISK = "CLEAR_RISK"              # Levantar marca de Riesgo de Venta (ej. deuda saldada)


class SaleRiskDecision(Base):
    __tablename__ = "sale_risk_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    order_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    order_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    client = relationship("Client", back_populates="risk_decisions")
    user = relationship("User")
