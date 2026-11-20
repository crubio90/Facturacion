import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScrapeStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ScrapeTriggerType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    ON_DEMAND = "ON_DEMAND"


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False, default=ScrapeTriggerType.ON_DEMAND.value)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ScrapeStatus.PENDING.value, index=True)

    triggered_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    clients_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoices_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invoices_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overdue_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    log_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    triggered_by = relationship("User")
