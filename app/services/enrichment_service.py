from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.services.company_service import get_company_by_id, update_company
from app.providers.enrichers.factory import EnricherFactory

async def run_enrichment_for_company(db: AsyncSession, company_id: UUID) -> Company:
    """
    Attempts to enrich company metadata using the configured ATS provider strategy.
    If successful, updates the company record (which triggers validation and status activation).
    """
    company = await get_company_by_id(db, company_id)

    if not company.ats_provider:
        logger.warning(f"Cannot enrich {company.name}: No ATS Provider specified.")
        return company

    enricher = EnricherFactory.get_enricher(company.ats_provider)
    if not enricher:
        logger.warning(f"No enricher strategy for {company.ats_provider}, skipping.")
        return company

    logger.info(f"Starting enrichment for {company.name} ({company.ats_provider})...")
    
    try:
        update_data = await enricher.enrich(company)
    except Exception as e:
        logger.error(f"Enrichment failed for {company.name}: {e}")
        return company

    if update_data:
        logger.success(f"Enrichment successful for {company.name}. Applying updates...")
        return await update_company(db, company_id, update_data)

    logger.info(f"Enrichment found no new data for {company.name}.")
    return company
