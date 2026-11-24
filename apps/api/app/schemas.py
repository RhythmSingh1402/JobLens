import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ExperienceItem(BaseModel):
    title: str
    company: str
    duration: str = Field(description="e.g. '2021-2023' or '2 years'")
    highlights: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    degree: str
    institution: str
    year: str | None = None


class CandidateProfile(BaseModel):
    """Structured extraction target for Gemini — the resume, distilled."""

    full_name: str | None = None
    email: str | None = None
    seniority: str = Field(description="e.g. junior, mid, senior, staff, lead")
    location: str | None = None
    summary: str = Field(description="2-3 sentence professional summary")
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)


class JobPostingOut(BaseModel):
    id: uuid.UUID
    source: str
    title: str
    company: str
    location: str
    seniority: str | None
    salary_range: str | None
    description: str
    requirements: list[str]
    url: str | None

    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    fetched: int
    inserted: int
    updated: int
    embedded: int


class MatchOut(BaseModel):
    id: uuid.UUID
    score: float
    rationale: str
    status: str
    cover_letter_subject: str | None
    cover_letter_body: str | None
    created_at: datetime
    job: JobPostingOut

    model_config = {"from_attributes": True}


class CoverLetter(BaseModel):
    """Structured extraction target for Gemini's cover-letter draft."""

    subject: str = Field(description="A concise email subject line for this application")
    body: str = Field(description="The full cover letter body, 3-4 short paragraphs")


class UploadResponse(BaseModel):
    candidate: CandidateProfile
    matches: list[MatchOut]


class CandidateOut(BaseModel):
    id: uuid.UUID
    full_name: str | None
    email: str | None
    seniority: str | None
    location: str | None
    summary: str | None
    skills: list[str]
    experience: list[ExperienceItem]
    education: list[EducationItem]

    model_config = {"from_attributes": True}
