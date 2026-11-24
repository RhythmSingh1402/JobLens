import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from google.genai import errors as genai_errors
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..constants import MOCK_CANDIDATE_ID
from ..database import get_db
from ..models import Candidate, JobPosting, Match
from ..schemas import MatchOut
from ..services.llm import describe_gemini_error, llm_service
from ..services.schemas_helpers import candidate_to_profile

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def list_matches(
    title: str | None = Query(None, description="Filter by job title (substring match)"),
    location: str | None = Query(None, description="Filter by location (substring match)"),
    seniority: str | None = Query(None, description="Filter by experience level (substring match)"),
    db: AsyncSession = Depends(get_db),
) -> list[Match]:
    stmt = (
        select(Match)
        .join(Match.job)
        .where(Match.candidate_id == MOCK_CANDIDATE_ID)
        .options(selectinload(Match.job))
    )
    if title:
        stmt = stmt.where(JobPosting.title.ilike(f"%{title}%"))
    if location:
        stmt = stmt.where(JobPosting.location.ilike(f"%{location}%"))
    if seniority:
        stmt = stmt.where(JobPosting.seniority.ilike(f"%{seniority}%"))
    stmt = stmt.order_by(Match.score.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/{match_id}/cover-letter", response_model=MatchOut)
async def generate_cover_letter(match_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Match:
    match = await db.get(Match, match_id, options=[selectinload(Match.job)])
    if match is None or match.candidate_id != MOCK_CANDIDATE_ID:
        raise HTTPException(404, "Match not found")

    candidate = await db.get(Candidate, MOCK_CANDIDATE_ID)
    if candidate is None:
        raise HTTPException(404, "No resume uploaded yet")

    profile = candidate_to_profile(candidate)
    try:
        letter = llm_service.generate_cover_letter(profile, match.job)
    except genai_errors.APIError as exc:
        status_code, message = describe_gemini_error(exc)
        raise HTTPException(status_code, message) from exc

    match.cover_letter_subject = letter.subject
    match.cover_letter_body = letter.body
    await db.commit()
    await db.refresh(match, attribute_names=["job"])

    return match
