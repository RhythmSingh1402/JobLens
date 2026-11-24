from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from ..config import settings
from ..models import JobPosting
from ..schemas import CandidateProfile, CoverLetter

MODEL = "gemini-2.5-flash"


def _quota_period(exc: genai_errors.APIError) -> str | None:
    """For a 429, returns the exhausted quota's reset period ('day' or 'minute') if it
    can be identified from the response body, else None. A per-day quota won't recover
    within a few backoff attempts, so it's pointless (and slow) to retry those."""
    details = getattr(exc, "details", None)
    if not isinstance(details, dict):
        return None
    for detail in details.get("error", {}).get("details", []):
        for violation in detail.get("violations", []):
            quota_id = violation.get("quotaId", "").lower()
            if "perday" in quota_id:
                return "day"
            if "perminute" in quota_id:
                return "minute"
    return None


def _is_retryable(exc: BaseException) -> bool:
    # 429 = rate/quota limit, 5xx = transient server error. Anything else (bad request,
    # auth) won't be fixed by retrying. A per-day quota exhaustion also won't be fixed
    # by retrying within seconds, so that's excluded too — fail fast instead.
    if not isinstance(exc, genai_errors.APIError):
        return False
    if exc.code == 429:
        return _quota_period(exc) != "day"
    return exc.code >= 500


def describe_gemini_error(exc: genai_errors.APIError) -> tuple[int, str]:
    """Maps a Gemini API error to (http_status, message) safe to show the user."""
    if exc.code == 429:
        if _quota_period(exc) == "day":
            return 429, (
                "Gemini's free-tier daily request quota is exhausted for this API key. "
                "Try again after it resets, or use a key with a paid plan."
            )
        return 429, "Gemini is rate-limited right now — please wait a moment and try again."
    if exc.code >= 500:
        return 503, "Gemini is temporarily unavailable — please try again shortly."
    return 502, f"Gemini request failed: {exc.message or 'unknown error'}"


_retry_gemini = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=40),
    reraise=True,
)


class LLMService:
    """Structured resume parsing and cover-letter drafting, powered by Gemini 2.5 Flash.
    Match scoring itself is handled by semantic search + the Hungarian algorithm (see
    services/matcher.py), not an LLM call."""

    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)

    @_retry_gemini
    def parse_resume(self, raw_text: str) -> CandidateProfile:
        prompt = (
            "Extract a structured candidate profile from the resume text below. "
            "Only use information present in the text; leave fields empty rather than guessing.\n\n"
            f"RESUME TEXT:\n{raw_text}"
        )
        response = self._client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CandidateProfile,
            ),
        )
        return CandidateProfile.model_validate_json(response.text)

    @_retry_gemini
    def generate_cover_letter(self, profile: CandidateProfile, job: JobPosting) -> CoverLetter:
        prompt = (
            "Write a short, specific cover letter draft for this candidate applying to this "
            "job. Reference concrete skills or experience from the candidate profile that "
            "match the job's requirements — no generic filler. Do not invent facts not present "
            "in the profile. This is a draft for the candidate to review before sending, not a "
            "final letter.\n\n"
            f"CANDIDATE:\n{profile.model_dump_json(indent=2)}\n\n"
            f"JOB:\nTitle: {job.title}\nCompany: {job.company}\nLocation: {job.location}\n"
            f"Requirements: {', '.join(job.requirements)}\nDescription: {job.description}"
        )
        response = self._client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CoverLetter,
            ),
        )
        return CoverLetter.model_validate_json(response.text)


llm_service = LLMService()
