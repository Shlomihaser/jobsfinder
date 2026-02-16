from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyStatus, ATSProvider


async def get_by_id(db: AsyncSession, company_id: UUID) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalars().first()

async def get_by_name_and_provider(db: AsyncSession, name: str, ats_provider: Optional[ATSProvider]) -> Optional[Company]:
    query = select(Company).where(Company.name == name)
    if ats_provider:
        query = query.where(Company.ats_provider == ats_provider)

    result = await db.execute(query)
    return result.scalars().first()

async def get_all(
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

async def create(db: AsyncSession, company: Company) -> Company:
    db.add(company)
    await db.flush()
    return company

async def update(db: AsyncSession, company: Company) -> Company:
    await db.flush()
    return company

async def delete(db: AsyncSession, company: Company) -> None:
    await db.delete(company)
    await db.flush()
