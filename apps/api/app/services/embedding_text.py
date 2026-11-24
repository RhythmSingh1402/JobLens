from ..models import JobPosting
from ..schemas import CandidateProfile


def job_embedding_text(job: JobPosting) -> str:
    return (
        f"{job.title} at {job.company} ({job.location}). "
        f"Requirements: {', '.join(job.requirements)}. {job.description}"
    )


def candidate_embedding_text(profile: CandidateProfile) -> str:
    experience_titles = ", ".join(f"{e.title} at {e.company}" for e in profile.experience)
    education = ", ".join(f"{ed.degree} ({ed.institution})" for ed in profile.education)
    return (
        f"{profile.seniority} candidate. {profile.summary} "
        f"Skills: {', '.join(profile.skills)}. Experience: {experience_titles}. "
        f"Education: {education}."
    )
