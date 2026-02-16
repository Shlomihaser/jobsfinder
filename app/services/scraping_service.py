from datetime import datetime, timezone
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CompanyNotFoundError, FatalProviderError
from app.models.company import CompanyStatus
from app.models.job import Job
from app.repositories import job_repository as job_repo
from app.providers.scrapers.factory import ScraperFactory
from app.schemas.job import JobSchema
from app.services.company_service import get_company_by_id


async def run_scrape_for_company(db: AsyncSession, company_id: UUID) -> int:
    """
    Scrapes jobs for a single company.
    Returns the number of new jobs found.
    """
    company = await get_company_by_id(db, company_id)

    if company.status != CompanyStatus.ACTIVE:
        logger.warning(f"{company.name}: Status is {company.status}, cannot scrape.")
        return 0

    scraper = ScraperFactory.get_scraper(company)
    logger.info(f"Scraping {company.name} ({company.ats_provider})...")

    try:
        scraped_jobs = await scraper.fetch_jobs()
    except FatalProviderError as e:
        logger.error(f"Fatal scrape error for {company.name}: {e}")
        company.status = CompanyStatus.ERROR
        await db.flush()
        raise
    except Exception as e:
        logger.error(f"Scrape failed for {company.name}: {e}")
        raise

    existing_ids = await job_repo.get_external_ids_by_company(db, company_id)
    scraped_ids = {job.external_id for job in scraped_jobs}

    new_count = 0
    updated_count = 0

    for job_data in scraped_jobs:
        if job_data.external_id in existing_ids:
            await _update_job(db, company_id, job_data)
            updated_count += 1
        else:
            await _create_job(db, company_id, job_data)
            new_count += 1

    archived_count = await job_repo.archive_missing(db, company_id, scraped_ids)

    company.last_scanned_at = datetime.now(timezone.utc)
    await db.flush()

    logger.success(
        f"{company.name}: {new_count} new, {updated_count} updated, {archived_count} archived"
    )
    return new_count


async def _create_job(db: AsyncSession, company_id: UUID, job_data: JobSchema) -> Job:
    job = Job(
        company_id=company_id,
        external_id=job_data.external_id,
        title=job_data.title,
        url=job_data.url,
        location=job_data.location,
        city=job_data.city,
        description=job_data.description,
        published_at=job_data.published_at,
        raw_data=job_data.raw_data,
    )
    return await job_repo.create(db, job)


async def _update_job(db: AsyncSession, company_id: UUID, job_data: JobSchema) -> None:
    job = await job_repo.get_by_external_id(db, company_id, job_data.external_id)
    if not job:
        return

    job.title = job_data.title
    job.url = job_data.url
    job.location = job_data.location
    job.city = job_data.city
    job.description = job_data.description
    job.published_at = job_data.published_at
    job.raw_data = job_data.raw_data
    job.last_scanned_at = datetime.now(timezone.utc)
