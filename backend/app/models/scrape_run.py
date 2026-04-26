import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, DateTime, ForeignKey, func, Integer, JSON, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.database import Base


class ScrapeRunStatus(str, enum.Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[ScrapeRunStatus] = mapped_column(
        SAEnum(ScrapeRunStatus, create_constraint=False, validate_strings=True, values_callable=lambda x: [e.value for e in x]),
        default=ScrapeRunStatus.RUNNING, nullable=False,
    )
    properties_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    properties_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    properties_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_log: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    source = relationship("Source", back_populates="scrape_runs")

    def __repr__(self):
        return f"<ScrapeRun {self.id} [{self.status.value}]>"
