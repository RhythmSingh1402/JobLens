from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import JobPosting
from .arbeitnow import ScrapedJob, fetch_jobs
from .embedding_text import job_embedding_text
from .embeddings import embedding_service

SOURCE = "arbeitnow"


def _content_changed(job: JobPosting, item: ScrapedJob) -> bool:
    return (
        job.title != item.title
        or job.company != item.company
        or job.location != item.location
        or job.seniority != item.seniority
        or job.description != item.description
        or job.requirements != item.requirements
        or job.url != item.url
    )


async def ingest_arbeitnow_jobs(db: AsyncSession, max_pages: int = 2) -> dict[str, int]:
    """Live-fetch jobs from Arbeitnow and upsert them, keyed on (source, external_id).

    Arbeitnow's free API has no keyword-search parameter (only `remote`/`visa_sponsorship`
    filters), so this pulls a broad recent slice rather than a query-filtered one — the
    "adequate to this candidate" narrowing happens afterward, in the matcher's semantic
    search + Hungarian scoring, not here.
    """
    scraped = fetch_jobs(max_pages=max_pages)

    existing = (
        (await db.execute(select(JobPosting).where(JobPosting.source == SOURCE))).scalars().all()
    )
    existing_by_external_id = {job.external_id: job for job in existing}

    inserted = 0
    updated = 0
    for item in scraped:
        job = existing_by_external_id.get(item.external_id)
        if job is None:
            job = JobPosting(source=SOURCE, external_id=item.external_id)
            db.add(job)
            job.title = item.title
            job.company = item.company
            job.location = item.location
            job.seniority = item.seniority
            job.description = item.description
            job.requirements = item.requirements
            job.url = item.url
            inserted += 1
        elif _content_changed(job, item):
            job.title = item.title
            job.company = item.company
            job.location = item.location
            job.seniority = item.seniority
            job.description = item.description
            job.requirements = item.requirements
            job.url = item.url
            job.embedding = None  # content changed — force re-embedding
            updated += 1
        # else: unchanged, leave its existing embedding alone — no need to re-embed
        # a job we've already seen on every single upload.

    await db.commit()

    embedded = await ensure_job_embeddings(db)

    return {"fetched": len(scraped), "inserted": inserted, "updated": updated, "embedded": embedded}


async def ensure_job_embeddings(db: AsyncSession) -> int:
    """Embed any job posting that doesn't have a vector yet (new or changed)."""
    jobs = (await db.execute(select(JobPosting).where(JobPosting.embedding.is_(None)))).scalars().all()
    if not jobs:
        return 0

    vectors = embedding_service.embed_texts([job_embedding_text(job) for job in jobs])
    for job, vector in zip(jobs, vectors):
        job.embedding = vector

    await db.commit()
    return len(jobs)
