from datetime import datetime
from uuid import UUID
from typing import Dict, Any, Optional
from pydantic import BaseModel, HttpUrl

from app.models.company import ATSProvider, CompanyStatus

class CompanyBase(BaseModel):
    name: str
    career_page_url: Optional[str] = None
    ats_provider: Optional[ATSProvider] = None
    metadata_config: Dict[str, Any] = {}
    status: Optional[CompanyStatus] = CompanyStatus.UNCONFIGURED

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(CompanyBase):
    name: Optional[str] = None
    career_page_url: Optional[str] = None
    ats_provider: Optional[ATSProvider] = None
    metadata_config: Optional[Dict[str, Any]] = None
    status: Optional[CompanyStatus] = None

class CompanyResponse(CompanyBase):
    id: UUID
    status: CompanyStatus = CompanyStatus.UNCONFIGURED
    last_scanned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
