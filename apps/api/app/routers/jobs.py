from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import JobPosting
from ..schemas import IngestResponse, JobPostingOut
from ..services.ingest import ingest_arbeitnow_jobs

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobPostingOut])
async def list_jobs(db: AsyncSession = Depends(get_db)) -> list[JobPosting]:
    result = await db.execute(select(JobPosting).order_by(JobPosting.title))
    return list(result.scalars().all())


@router.post("/ingest", response_model=IngestResponse)
async def ingest_jobs(
    pages: int = Query(3, ge=1, le=20, description="Number of Arbeitnow pages to pull (100 jobs each)"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    return await ingest_arbeitnow_jobs(db, max_pages=pages)
