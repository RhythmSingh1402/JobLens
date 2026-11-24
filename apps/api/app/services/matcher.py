import numpy as np
from scipy.optimize import linear_sum_assignment
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Candidate, JobPosting, Match
from ..schemas import CandidateProfile
from .embedding_text import candidate_embedding_text
from .embeddings import DIMENSION, embedding_service
from .schemas_helpers import candidate_to_profile

# How many jobs the semantic-search step shortlists for the (more expensive) Hungarian
# scoring pass. This is what lets matching scale to a large scraped catalog instead of
# scoring every job in the table.
TOP_K = 30

# Cosine similarity floor for a candidate item to count as "covering" a job requirement.
# Real mistral-embed similarities for short, generic phrases run higher than intuition
# suggests (embedding-space anisotropy) — 0.5 let through nonsense pairs like "Git" ->
# "Business Consulting" in practice, so this is set conservatively high. Tune based on
# real usage, not synthetic tests.
STRONG_MATCH_THRESHOLD = 0.72

# Cap on how many candidate items (skills + experience + education) feed the Hungarian
# assignment, so a very long resume doesn't blow up the cost matrix. Skills, experience
# titles, and education come first (highest signal); highlights are truncated first.
MAX_CANDIDATE_ITEMS = 40


def _build_candidate_items(profile: CandidateProfile) -> list[str]:
    """Every distinct thing about the candidate that could plausibly satisfy a job
    requirement: skills, past roles, degrees, and specific experience highlights —
    not just the skills list. A requirement like "5+ years experience" or "distributed
    systems" is often only satisfiable by an experience entry, not a bare skill tag."""
    items: list[str] = list(profile.skills)
    for exp in profile.experience:
        items.append(f"{exp.title} at {exp.company}" if exp.company else exp.title)
    for edu in profile.education:
        items.append(f"{edu.degree}, {edu.institution}" if edu.institution else edu.degree)
    for exp in profile.experience:
        items.extend(exp.highlights)
    return list(dict.fromkeys(item for item in items if item))[:MAX_CANDIDATE_ITEMS]


def _cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = a / np.clip(np.linalg.norm(a, axis=1, keepdims=True), 1e-9, None)
    b_norm = b / np.clip(np.linalg.norm(b, axis=1, keepdims=True), 1e-9, None)
    return a_norm @ b_norm.T


def _score_job(
    candidate_items: list[str],
    candidate_vecs: np.ndarray,
    requirements: list[str],
    requirement_vecs: np.ndarray,
) -> tuple[float, str]:
    """Optimal one-to-one assignment (skills, experience, and education, all together)
    against job requirements, via the Hungarian algorithm.

    Score = sum of similarities for assignment pairs that clear the "strong match"
    threshold, normalized by the job's requirement count — so a job whose requirements
    are only partially covered (or covered weakly) scores proportionally lower, not
    just averaged over however many pairs happened to get assigned.
    """
    if not candidate_items or not requirements:
        return 0.0, "No comparable profile items or requirements to evaluate."

    similarity = _cosine_similarity_matrix(candidate_vecs, requirement_vecs)
    row_ind, col_ind = linear_sum_assignment(-similarity)  # maximize similarity

    covered: list[tuple[str, str, float]] = []
    covered_requirements: set[str] = set()
    for r, c in zip(row_ind, col_ind):
        sim = float(similarity[r, c])
        if sim >= STRONG_MATCH_THRESHOLD:
            covered.append((candidate_items[r], requirements[c], sim))
            covered_requirements.add(requirements[c])

    score = round(100 * min(sum(sim for _, _, sim in covered) / len(requirements), 1.0), 1)

    missing = [req for req in requirements if req not in covered_requirements]
    if covered:
        top = sorted(covered, key=lambda c: -c[2])[:4]
        rationale = (
            f"Optimal profile assignment covers {len(covered_requirements)}/{len(requirements)} "
            f"requirements ({', '.join(f'{item}→{req}' for item, req, _ in top)})."
        )
    else:
        rationale = "No strong overlap between your profile (skills, experience, education) and this job's requirements."
    if missing:
        rationale += f" Not covered: {', '.join(missing[:4])}."

    return score, rationale


async def run_matching(db: AsyncSession, candidate: Candidate) -> list[Match]:
    """Two-stage matching: pgvector semantic search shortlists the top-K most relevant
    jobs by whole-profile embedding similarity, then each shortlisted job is scored by
    solving the optimal assignment (Hungarian algorithm) between the candidate's skills,
    experience, and education and the job's requirements — deterministic, no LLM call,
    and scales to a large ingested job catalog.
    """
    profile = candidate_to_profile(candidate)

    await db.execute(delete(Match).where(Match.candidate_id == candidate.id))

    candidate_vec = embedding_service.embed_texts([candidate_embedding_text(profile)])[0]

    stmt = (
        select(JobPosting)
        .where(JobPosting.embedding.is_not(None))
        .order_by(JobPosting.embedding.cosine_distance(candidate_vec))
        .limit(TOP_K)
    )
    jobs = (await db.execute(stmt)).scalars().all()

    candidate_items = _build_candidate_items(profile)
    candidate_item_vecs_by_item = (
        dict(zip(candidate_items, embedding_service.embed_texts(candidate_items))) if candidate_items else {}
    )
    all_requirements = sorted({req for job in jobs for req in job.requirements})
    requirement_vecs_by_req = (
        dict(zip(all_requirements, embedding_service.embed_texts(all_requirements))) if all_requirements else {}
    )

    matches: list[Match] = []
    for job in jobs:
        requirements = job.requirements
        if candidate_items and requirements:
            item_vecs = np.array([candidate_item_vecs_by_item[i] for i in candidate_items])
            requirement_vecs = np.array([requirement_vecs_by_req[r] for r in requirements])
        else:
            item_vecs = np.empty((0, DIMENSION))
            requirement_vecs = np.empty((0, DIMENSION))

        score, rationale = _score_job(candidate_items, item_vecs, requirements, requirement_vecs)

        match = Match(
            candidate_id=candidate.id,
            job_id=job.id,
            score=score,
            rationale=rationale,
            status="new",
        )
        db.add(match)
        matches.append(match)

    await db.commit()

    for match in matches:
        await db.refresh(match, attribute_names=["job"])

    matches.sort(key=lambda m: m.score, reverse=True)
    return matches
