from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate

async def get_company_by_id(db: AsyncSession, company_id: UUID) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalars().first()

from app.models.company import Company, CompanyStatus, ATSProvider

async def get_companies(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    name: Optional[str] = None,
    status: Optional[CompanyStatus] = None,
    ats_provider: Optional[ATSProvider] = None
) -> List[Company]:
    query = select(Company)
    
    if name:
        query = query.where(Company.name.ilike(f"%{name}%"))
    if status:
        query = query.where(Company.status == status)
    if ats_provider:
        query = query.where(Company.ats_provider == ats_provider)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

from app.services.scrapers.factory import ScraperFactory
from app.models.company import CompanyStatus

from fastapi import HTTPException

async def create_company(db: AsyncSession, company_in: CompanyCreate) -> Company:
    final_status = CompanyStatus.UNCONFIGURED
    
    # 1. Check Config Validity
    is_valid_config = False
    if company_in.ats_provider and company_in.metadata_config:
        is_valid_config = await ScraperFactory.validate_provider_config(company_in.ats_provider, company_in.metadata_config)

    # 2. Assign Status
    if company_in.status == CompanyStatus.ACTIVE:
        if not is_valid_config:
            raise HTTPException(status_code=400, detail="Cannot set status to ACTIVE with invalid configuration.")
        final_status = CompanyStatus.ACTIVE
    elif is_valid_config:
        final_status = CompanyStatus.ACTIVE
    elif company_in.status:
        final_status = company_in.status

    db_company = Company(
        name=company_in.name,
        career_page_url=company_in.career_page_url,
        ats_provider=company_in.ats_provider,
        metadata_config=company_in.metadata_config,
        status=final_status
    )
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    return db_company

async def update_company(db: AsyncSession, company_id: UUID, company_in: CompanyUpdate) -> Optional[Company]:
    company = await get_company_by_id(db, company_id)
    if not company:
        return None

    # Apply Updates
    if company_in.name is not None:
        company.name = company_in.name
    if company_in.career_page_url is not None:
        company.career_page_url = company_in.career_page_url
    if company_in.status is not None:
        company.status = company_in.status
    if company_in.ats_provider is not None:
        company.ats_provider = company_in.ats_provider
    if company_in.metadata_config is not None:
        company.metadata_config = company_in.metadata_config
    # Validation Logic
    is_valid = False
    if company.ats_provider and company.metadata_config:
        is_valid = await ScraperFactory.validate_provider_config(company.ats_provider, company.metadata_config)
    
    current_status = company.status

    if is_valid:
        # Config is GOOD
        if current_status == CompanyStatus.UNCONFIGURED:
             # If user explicitly requested UNCONFIGURED -> Error
             if company_in.status == CompanyStatus.UNCONFIGURED:
                 raise HTTPException(status_code=400, detail="Configuration is valid. Cannot set UNCONFIGURED. Use INACTIVE to pause scraping.")
             
             # Otherwise (Implicit update of config) -> Auto-Upgrade to ACTIVE
             company.status = CompanyStatus.ACTIVE
    else:
        # Config is BAD
        if current_status in [CompanyStatus.ACTIVE, CompanyStatus.INACTIVE]:
             # If user explicitly forced bad status -> Error
             if company_in.status in [CompanyStatus.ACTIVE, CompanyStatus.INACTIVE]:
                 raise HTTPException(status_code=400, detail="Configuration is invalid. Cannot set status to ACTIVE or INACTIVE.")
             
             # Otherwise (Implicit break of config) -> Downgrade
             company.status = CompanyStatus.UNCONFIGURED
        
        # Ensure status is not stranded in invalid state
        if company.status not in [CompanyStatus.UNCONFIGURED, CompanyStatus.ERROR]:
             company.status = CompanyStatus.UNCONFIGURED

    await db.commit()
    await db.refresh(company)
    return company

async def delete_company(db: AsyncSession, company_id: UUID) -> bool:
    company = await get_company_by_id(db, company_id)
    if company:
        await db.delete(company)
        await db.commit()
        return True
    return False
