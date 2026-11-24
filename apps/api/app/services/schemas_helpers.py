from ..models import Candidate
from ..schemas import CandidateProfile


def candidate_to_profile(candidate: Candidate) -> CandidateProfile:
    return CandidateProfile(
        full_name=candidate.full_name,
        email=candidate.email,
        seniority=candidate.seniority or "unknown",
        location=candidate.location,
        summary=candidate.summary or "",
        skills=candidate.skills or [],
        experience=candidate.experience or [],
        education=candidate.education or [],
    )
