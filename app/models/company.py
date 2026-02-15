import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

class ATSProvider(str, enum.Enum):
    GREENHOUSE = "GREENHOUSE"
    COMEET = "COMEET"
    WORKDAY = "WORKDAY"
    LEVER = "LEVER"
    API_CUSTOM = "API_CUSTOM"

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = mapped_column(default=uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    career_page_url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    
    ats_identifier: Mapped[str | None] = mapped_column(String, nullable=True)
    ats_provider: Mapped[ATSProvider | None] = mapped_column(SQLEnum(ATSProvider), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    metadata_config: Mapped[dict] = mapped_column(JSONB, default={}) 
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), server_default=func.now())

    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")