import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReminderStatus(str, enum.Enum):
    SENT = "SENT"
    DRY_RUN = "DRY_RUN"
    FAILED = "FAILED"


class ReminderTriggerType(str, enum.Enum):
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class PaymentReminder(Base):
    __tablename__ = "payment_reminders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    invoice_ids: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    invoice_folios: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)

    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_preview: Mapped[str] = mapped_column(Text, nullable=False)

    reminder_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ReminderStatus.SENT.value)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    trigger_type: Mapped[str] = mapped_column(
        String(20),
        default=ReminderTriggerType.MANUAL.value,
        nullable=False,
    )
    triggered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    client = relationship("Client", back_populates="reminders")
    invoice = relationship("Invoice", back_populates="reminders")
    triggered_by = relationship("User")
