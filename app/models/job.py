import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base

class JobStatus(str, enum.Enum):
    NEW = "NEW"
    APPLIED = "APPLIED"
    ARCHIVED = "ARCHIVED"

class UserVerdict(str, enum.Enum):
    PERFECT_MATCH = "PERFECT_MATCH"
    GOOD = "GOOD"
    IRRELEVANT = "IRRELEVANT"

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    
    title: Mapped[str] = mapped_column(String, index=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    city: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    
    raw_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.NEW, index=True)
    user_verdict: Mapped[UserVerdict | None] = mapped_column(SQLEnum(UserVerdict), nullable=True)

    company = relationship("Company", back_populates="jobs")

    __table_args__ = (
        UniqueConstraint("company_id", "external_id", name="uq_company_job"),
    )