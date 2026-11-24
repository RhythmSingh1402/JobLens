from fastapi import APIRouter, Depends, HTTPException, UploadFile
from google.genai import errors as genai_errors
from mistralai.client.errors import MistralError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..constants import MOCK_CANDIDATE_ID
from ..database import get_db
from ..models import Candidate
from ..schemas import CandidateOut, UploadResponse
from ..services.ingest import ingest_arbeitnow_jobs
from ..services.matcher import run_matching
from ..services.mistral_client import describe_mistral_error
from ..services.ocr import ocr_service
from ..services.llm import describe_gemini_error, llm_service

router = APIRouter(prefix="/resumes", tags=["resumes"])

ALLOWED_MIME_TYPES = {"application/pdf", "image/png", "image/jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(file: UploadFile, db: AsyncSession = Depends(get_db)) -> UploadResponse:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File exceeds 10MB limit")
    if not contents:
        raise HTTPException(400, "Empty file")

    try:
        raw_text = ocr_service.extract_text(contents, file.content_type)
        if not raw_text.strip():
            raise HTTPException(422, "Could not extract any text from this file. Try a clearer scan.")

        profile = llm_service.parse_resume(raw_text)

        candidate = await db.get(Candidate, MOCK_CANDIDATE_ID)
        if candidate is None:
            candidate = Candidate(id=MOCK_CANDIDATE_ID)
            db.add(candidate)

        candidate.full_name = profile.full_name
        candidate.email = profile.email
        candidate.seniority = profile.seniority
        candidate.location = profile.location
        candidate.summary = profile.summary
        candidate.skills = profile.skills
        candidate.experience = [item.model_dump() for item in profile.experience]
        candidate.education = [item.model_dump() for item in profile.education]
        candidate.raw_resume_text = raw_text

        await db.commit()
        await db.refresh(candidate)

        # Live search: refresh the job catalog from Arbeitnow on every upload, rather than
        # matching against a stale (or empty) table. Jobs already seen and unchanged since
        # a previous upload are cheap — only new/changed ones get re-embedded.
        await ingest_arbeitnow_jobs(db)

        matches = await run_matching(db, candidate)
    except genai_errors.APIError as exc:
        status_code, message = describe_gemini_error(exc)
        raise HTTPException(status_code, message) from exc
    except MistralError as exc:
        status_code, message = describe_mistral_error(exc)
        raise HTTPException(status_code, message) from exc

    return UploadResponse(candidate=profile, matches=matches)


@router.get("/me", response_model=CandidateOut)
async def get_current_candidate(db: AsyncSession = Depends(get_db)):
    candidate = await db.get(Candidate, MOCK_CANDIDATE_ID)
    if candidate is None:
        raise HTTPException(404, "No resume uploaded yet")
    return candidate
