from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus


async def get_by_company(db: AsyncSession, company_id: UUID) -> List[Job]:
    result = await db.execute(
        select(Job).where(Job.company_id == company_id)
    )
    return result.scalars().all()

async def get_external_ids_by_company(db: AsyncSession, company_id: UUID) -> Set[str]:
    result = await db.execute(
        select(Job.external_id).where(Job.company_id == company_id)
    )
    return {row[0] for row in result.all()}

async def get_by_external_id(db: AsyncSession, company_id: UUID, external_id: str) -> Optional[Job]:
    result = await db.execute(
        select(Job).where(
            Job.company_id == company_id,
            Job.external_id == external_id,
        )
    )
    return result.scalars().first()

async def create(db: AsyncSession, job: Job) -> Job:
    db.add(job)
    await db.flush()
    return job

async def archive_missing(db: AsyncSession, company_id: UUID, active_external_ids: Set[str]) -> int:
    """Mark jobs not in the latest scrape as ARCHIVED. Returns count of archived jobs."""
    result = await db.execute(
        update(Job)
        .where(
            Job.company_id == company_id,
            Job.external_id.notin_(active_external_ids),
            Job.status != JobStatus.ARCHIVED,
        )
        .values(status=JobStatus.ARCHIVED)
    )
    return result.rowcount
