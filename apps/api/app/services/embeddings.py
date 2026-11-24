from mistralai.client import Mistral

from ..config import settings
from .mistral_client import retry_mistral

MODEL = "mistral-embed"
DIMENSION = 1024

# The API takes a batch of inputs per call; keep batches well under its request-size
# limits when embedding a large scraped catalog.
BATCH_SIZE = 64


class EmbeddingService:
    """Text embeddings via Mistral's `mistral-embed`, used for both the coarse
    semantic-search retrieval step and the fine-grained skill/requirement vectors
    that feed the Hungarian assignment."""

    def __init__(self) -> None:
        self._client = Mistral(api_key=settings.mistral_api_key)

    @retry_mistral
    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=MODEL, inputs=texts)
        by_index = {item.index: item.embedding for item in response.data}
        return [by_index[i] for i in range(len(texts))]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        results: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            results.extend(self._embed_batch(texts[start : start + BATCH_SIZE]))
        return results


embedding_service = EmbeddingService()
