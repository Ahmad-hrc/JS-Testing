"""RAG answer generation — constructs grounded answers with source citations."""

import logging
from dataclasses import dataclass

from ingestion.vector_store import Chunk

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.5
LOW_CONFIDENCE_DISCLAIMER = (
    "\n\n⚠️ Note: The retrieved context had low relevance to your query. "
    "Please verify this answer directly in the source documents."
)


@dataclass
class RAGAnswer:
    answer: str
    sources: list[dict]
    confidence: float


def build_rag_prompt(question: str, chunks: list[tuple[Chunk, float]]) -> str:
    """Build a prompt that grounds the LLM in retrieved context."""
    if not chunks:
        return (
            f"The user asked: {question}\n\n"
            "No relevant documents were found in the HR rollout document corpus. "
            "Please tell the user that the information is not available in the indexed documents."
        )

    context_parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}] Document: {chunk.source_doc} | Section: {chunk.section}\n{chunk.text}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return (
        f"Answer the following question using ONLY the context provided below. "
        f"Cite each source document and section in your answer. "
        f"If the answer is not in the context, say so explicitly.\n\n"
        f"Question: {question}\n\n"
        f"Context:\n{context}"
    )


def format_rag_answer(llm_response: str, chunks: list[tuple[Chunk, float]]) -> RAGAnswer:
    """Format the LLM response into a structured RAGAnswer."""
    top_score = chunks[0][1] if chunks else 0.0
    sources = [
        {"document": c.source_doc, "section": c.section, "relevance": round(score, 3)}
        for c, score in chunks
    ]
    answer = llm_response
    if top_score < CONFIDENCE_THRESHOLD and chunks:
        answer += LOW_CONFIDENCE_DISCLAIMER
    return RAGAnswer(answer=answer, sources=sources, confidence=top_score)
