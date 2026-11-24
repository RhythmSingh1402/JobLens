import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

EMBEDDING_DIM = 1024  # mistral-embed output size


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    experience: Mapped[list] = mapped_column(JSONB, default=list)
    education: Mapped[list] = mapped_column(JSONB, default=list)
    raw_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    matches: Mapped[list["Match"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_job_source_external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(50), default="seed")
    external_id: Mapped[str] = mapped_column(String(255))
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(255))
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[list] = mapped_column(JSONB, default=list)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    matches: Mapped[list["Match"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("candidate_id", "job_id", name="uq_match_candidate_job"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidates.id", ondelete="CASCADE"))
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_postings.id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new")
    cover_letter_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cover_letter_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    candidate: Mapped[Candidate] = relationship(back_populates="matches")
    job: Mapped[JobPosting] = relationship(back_populates="matches")
