from mistralai.client.errors import MistralError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, MistralError) and (exc.status_code == 429 or exc.status_code >= 500)


retry_mistral = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=40),
    reraise=True,
)


def describe_mistral_error(exc: MistralError) -> tuple[int, str]:
    """Maps a Mistral API error to (http_status, message) safe to show the user."""
    if exc.status_code == 429:
        return 429, "Mistral is rate-limited right now — please wait a moment and try again."
    if exc.status_code >= 500:
        return 503, "Mistral is temporarily unavailable — please try again shortly."
    return 502, f"Mistral request failed: {exc.message or 'unknown error'}"
