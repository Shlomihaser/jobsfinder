from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyAlreadyExistsError, CompanyNotFoundError, CompanyValidationError
from app.models.company import Company, CompanyStatus, ATSProvider
from app.repositories import company_repository as company_repo
from app.schemas.company import CompanyCreate, CompanyUpdate
from app.providers.scrapers.factory import ScraperFactory


async def _check_config_validity(ats_provider: Optional[ATSProvider], metadata_config: Optional[dict]) -> bool:
    """Safely checks config validity. Returns False on any error (e.g. provider is down)."""
    if not ats_provider or not metadata_config:
        return False
    try:
        return await ScraperFactory.validate_provider_config(ats_provider, metadata_config)
    except Exception as e:
        logger.warning(f"Config validation failed for {ats_provider}: {e}")
        return False


async def _resolve_status(
    current_status: CompanyStatus,
    requested_status: Optional[CompanyStatus],
    is_valid_config: bool,
) -> CompanyStatus:
    """
    Single source of truth for company status transitions.
    Determines the final status based on config validity and what the caller requested.
    """
    if requested_status == CompanyStatus.ERROR:
        raise CompanyValidationError("ERROR is a system-managed status. Use INACTIVE to pause scraping.")

    if is_valid_config:
        if requested_status == CompanyStatus.ACTIVE:
            return CompanyStatus.ACTIVE
        if requested_status == CompanyStatus.UNCONFIGURED:
            raise CompanyValidationError("Configuration is valid. Cannot set UNCONFIGURED. Use INACTIVE to pause scraping.")
        if requested_status == CompanyStatus.INACTIVE:
            return CompanyStatus.INACTIVE
        if current_status == CompanyStatus.UNCONFIGURED:
            return CompanyStatus.ACTIVE

        return current_status
    else:
        if requested_status in [CompanyStatus.ACTIVE, CompanyStatus.INACTIVE]:
            raise CompanyValidationError("Configuration is invalid. Cannot set status to ACTIVE or INACTIVE.")
        if requested_status == CompanyStatus.UNCONFIGURED:
            return CompanyStatus.UNCONFIGURED
        if current_status in [CompanyStatus.ACTIVE, CompanyStatus.INACTIVE]:
            return CompanyStatus.UNCONFIGURED
        if current_status == CompanyStatus.ERROR:
            return CompanyStatus.ERROR

        return CompanyStatus.UNCONFIGURED


async def get_companies(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    name: Optional[str] = None,
    status: Optional[CompanyStatus] = None,
    ats_provider: Optional[ATSProvider] = None
) -> List[Company]:
    return await company_repo.get_all(db, skip, limit, name, status, ats_provider)


async def get_company_by_id(db: AsyncSession, company_id: UUID) -> Company:
    company = await company_repo.get_by_id(db, company_id)
    if not company:
        raise CompanyNotFoundError(f"Company {company_id} not found")
    return company


async def create_company(db: AsyncSession, company_in: CompanyCreate) -> Company:
    existing = await company_repo.get_by_name_and_provider(db, company_in.name, company_in.ats_provider)
    if existing:
        raise CompanyAlreadyExistsError(f"Company '{company_in.name}' with ATS '{company_in.ats_provider}' already exists")

    is_valid = await _check_config_validity(company_in.ats_provider, company_in.metadata_config)
    final_status = await _resolve_status(CompanyStatus.UNCONFIGURED, company_in.status, is_valid)
    
    db_company = Company(
        name=company_in.name,
        career_page_url=company_in.career_page_url,
        ats_provider=company_in.ats_provider,
        metadata_config=company_in.metadata_config,
        status=final_status,
    )
    return await company_repo.create(db, db_company)


async def update_company(db: AsyncSession, company_id: UUID, company_in: CompanyUpdate) -> Company:
    company = await get_company_by_id(db, company_id)

    if company_in.name is not None:
        company.name = company_in.name
    if company_in.career_page_url is not None:
        company.career_page_url = company_in.career_page_url
    if company_in.ats_provider is not None:
        company.ats_provider = company_in.ats_provider
    if company_in.metadata_config is not None:
        company.metadata_config = company_in.metadata_config

    is_valid = await _check_config_validity(company.ats_provider, company.metadata_config)
    company.status = await _resolve_status(company.status, company_in.status, is_valid)

    return await company_repo.update(db, company)


async def delete_company(db: AsyncSession, company_id: UUID) -> None:
    company = await get_company_by_id(db, company_id)
    await company_repo.delete(db, company)

