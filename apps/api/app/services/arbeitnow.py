import html
import re
from dataclasses import dataclass

import httpx

API_URL = "https://www.arbeitnow.com/api/job-board-api"
PER_PAGE = 100  # fixed by the API

# Arbeitnow's `job_types` are a mix of seniority and contract-type tags (mostly German).
# Map the ones that signal seniority; anything unmapped is left as None rather than guessed.
SENIORITY_MAP = {
    "berufseinstieg": "junior",
    "berufserfahren": "mid",
    "teamleitung": "lead",
    "manager": "senior",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")

# Arbeitnow's `tags` field is inconsistent: alongside genuine topical/domain categories
# (e.g. "Software Development", "Finance"), it sometimes also contains contract-type,
# seniority, or education-level descriptors (e.g. "bachelor's degree", "Remote",
# "berufserfahren") that also show up in `job_types`. Matching candidate skills against
# these produces nonsense pairings (e.g. "Git" -> "Remote"), so they're excluded from
# `requirements` regardless of which field they came from.
_NON_SKILL_TAGS = {
    "remote", "freelance", "contract", "internship", "working student", "traineeship",
    "apprenticeship", "dual studies", "part-time", "temporary",
    "berufserfahren", "berufseinstieg", "hilfstätigkeit / student", "geschäftsleitung",
    "professional / experienced", "entry", "experienced", "mid", "senior", "junior", "lead",
    "manager", "teamleitung", "vocational",
}
_NON_SKILL_SUBSTRINGS = ("degree", "high school", "full-time", "full time")


def _is_skill_tag(tag: str) -> bool:
    lowered = tag.strip().lower()
    if lowered in _NON_SKILL_TAGS:
        return False
    return not any(s in lowered for s in _NON_SKILL_SUBSTRINGS)


def _strip_html(raw: str) -> str:
    text = _TAG_RE.sub(" ", raw)
    text = html.unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _derive_seniority(job_types: list[str]) -> str | None:
    for job_type in job_types:
        if job_type in SENIORITY_MAP:
            return SENIORITY_MAP[job_type]
    return None


@dataclass
class ScrapedJob:
    external_id: str
    title: str
    company: str
    location: str
    seniority: str | None
    description: str
    requirements: list[str]
    url: str


def _normalize(raw: dict) -> ScrapedJob:
    location = raw.get("location") or ("Remote" if raw.get("remote") else "Unspecified")
    description = _strip_html(raw.get("description") or "")[:4000]
    # `job_types` is contract-type/seniority metadata, used only for seniority below —
    # never as a requirement. `tags` are topical/skill-ish, but inconsistently also
    # contain the same kind of metadata (see _is_skill_tag), which gets filtered out.
    requirements = [t for t in dict.fromkeys(raw.get("tags", [])) if _is_skill_tag(t)]

    return ScrapedJob(
        external_id=raw["slug"],
        title=raw["title"],
        company=raw["company_name"],
        location=location,
        seniority=_derive_seniority(raw.get("job_types", [])),
        description=description,
        requirements=requirements,
        url=raw["url"],
    )


def fetch_jobs(max_pages: int = 3) -> list[ScrapedJob]:
    """Fetch up to `max_pages` pages (100 jobs each) from Arbeitnow's free public API.

    No auth required. Their terms just ask not to abuse the endpoint, so pages are
    fetched sequentially with a real client (one request per page, not parallelized).
    """
    jobs: list[ScrapedJob] = []
    with httpx.Client(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            response = client.get(API_URL, params={"page": page})
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data", [])
            if not data:
                break
            jobs.extend(_normalize(raw) for raw in data)
            if not payload.get("links", {}).get("next"):
                break
    return jobs
