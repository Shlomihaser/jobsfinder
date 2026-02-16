from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.api.services.company_service import create_company, get_companies, get_company_by_id, delete_company, update_company

router = APIRouter()

@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_company(
    company_in: CompanyCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new company.
    """
    # Check if exists (Name + ATS Provider)
    existing = await db.execute(
        select(Company).where(
            Company.name == company_in.name,
            Company.ats_provider == company_in.ats_provider
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status_code=400, 
            detail=f"Company '{company_in.name}' with ATS '{company_in.ats_provider}' already exists"
        )

    return await create_company(db, company_in)

from app.models.company import Company, CompanyStatus, ATSProvider

@router.get("/", response_model=List[CompanyResponse])
async def list_companies(
    name: Optional[str] = None,
    status: Optional[CompanyStatus] = None,
    ats_provider: Optional[ATSProvider] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db)
):
    """
    List all companies with optional filtering.
    """
    return await get_companies(
        db, 
        skip=skip, 
        limit=limit,
        name=name,
        status=status,
        ats_provider=ats_provider
    )

@router.get("/{company_id}", response_model=CompanyResponse)
async def read_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific company by ID.
    """
    company = await get_company_by_id(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company_details(
    company_id: UUID, 
    company_in: CompanyUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update company details (name, credentials, status).
    """
    updated_company = await update_company(db, company_id, company_in)
    if not updated_company:
        raise HTTPException(status_code=404, detail="Company not found")
    return updated_company

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a company.
    """
    success = await delete_company(db, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return None
