"""Embedding generation via SAP AI Core LiteLLM."""

import logging
import os

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = os.environ.get("AICORE_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = 1536  # default for text-embedding-3-small


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using LiteLLM.

    Returns a list of float vectors, one per input text.
    Falls back to zero vectors when AI Core is unavailable (test/dev mode).
    """
    if not texts:
        return []
    try:
        import litellm  # type: ignore
        response = litellm.embedding(model=EMBEDDING_MODEL, input=texts)
        return [item["embedding"] for item in response.data]
    except Exception as exc:
        logger.warning("Embedding generation failed (%s) — using zero vectors", exc)
        return [[0.0] * EMBEDDING_DIM for _ in texts]


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    results = embed_texts([text])
    return results[0] if results else [0.0] * EMBEDDING_DIM
