"""In-memory vector store backed by numpy cosine similarity."""

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    source_doc: str
    section: str
    rollout_name: str
    doc_type: str = "unknown"
    embedding: list[float] = field(default_factory=list)


class VectorStore:
    """Simple in-memory vector store scoped by rollout initiative."""

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def upsert(self, chunks: list[Chunk], rollout_name: str) -> None:
        # Remove old chunks for this rollout + source combo
        sources = {c.source_doc for c in chunks}
        self._chunks = [
            c for c in self._chunks
            if not (c.rollout_name == rollout_name and c.source_doc in sources)
        ]
        for c in chunks:
            c.rollout_name = rollout_name
        self._chunks.extend(chunks)
        logger.debug("Upserted %d chunks for rollout '%s'", len(chunks), rollout_name)

    def search(self, query_embedding: list[float], rollout_name: str | None, top_k: int = 5) -> list[tuple[Chunk, float]]:
        candidates = [
            c for c in self._chunks
            if (rollout_name is None or c.rollout_name == rollout_name) and c.embedding
        ]
        if not candidates:
            return []
        qv = np.array(query_embedding, dtype=float)
        scores = []
        for c in candidates:
            cv = np.array(c.embedding, dtype=float)
            norm = np.linalg.norm(qv) * np.linalg.norm(cv)
            score = float(np.dot(qv, cv) / norm) if norm > 0 else 0.0
            scores.append((c, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_by_doc(self, source_doc: str, rollout_name: str) -> list[Chunk]:
        return [c for c in self._chunks if c.source_doc == source_doc and c.rollout_name == rollout_name]

    def get_by_rollout(self, rollout_name: str) -> list[Chunk]:
        return [c for c in self._chunks if c.rollout_name == rollout_name]

    def count(self, rollout_name: str) -> int:
        return sum(1 for c in self._chunks if c.rollout_name == rollout_name)

    def doc_types_present(self, rollout_name: str) -> set[str]:
        return {c.doc_type for c in self._chunks if c.rollout_name == rollout_name}

    def clear_rollout(self, rollout_name: str) -> None:
        self._chunks = [c for c in self._chunks if c.rollout_name != rollout_name]


# Shared singleton
_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def reset_vector_store() -> None:
    """Reset singleton — for tests only."""
    global _store
    _store = None
