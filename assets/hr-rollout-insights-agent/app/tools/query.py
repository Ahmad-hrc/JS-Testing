"""Natural language Q&A tool — retrieves relevant chunks and generates grounded answers."""

import logging
from typing import Optional

from langchain_core.tools import tool

from ingestion.embedder import embed_query
from ingestion.vector_store import get_vector_store
from rag.answerer import build_rag_prompt, format_rag_answer
from utils.rollout_resolver import resolve_rollout_name
from registry import get_registry

logger = logging.getLogger(__name__)

TOP_K = 5


@tool
def query_rollout_documents(question: str, rollout_name: Optional[str] = None) -> str:
    """Answer a natural language question from HR rollout documents.

    Use this tool to answer questions about rollout scope, timelines, decisions,
    tasks, policies, or any other content in the indexed documents.

    Args:
        question: The natural language question to answer.
        rollout_name: Optional rollout initiative name to scope the search.
                      If not provided, searches across all indexed documents.

    Returns:
        A source-grounded answer with document and section citations.
    """
    store = get_vector_store()
    registry = get_registry()

    # Resolve rollout scope
    resolved_name = rollout_name
    if rollout_name:
        resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
        if resolved is None:
            return (
                f"No rollout initiative matching '{rollout_name}' was found. "
                f"Available initiatives: {', '.join(registry.all_names()) or 'none'}. "
                "Please check the name or use list_rollout_initiatives to see all options."
            )
        if not is_exact:
            resolved_name = resolved

    query_embedding = embed_query(question)
    results = store.search(query_embedding, resolved_name, top_k=TOP_K)

    if not results:
        logger.warning(
            "M3.missed: Q&A could not be resolved — rollout %s, no relevant documents found for query",
            resolved_name or "all",
        )
        return (
            f"No relevant documents were found"
            + (f" for rollout '{resolved_name}'" if resolved_name else "")
            + ". Please ensure documents have been ingested using the ingest_documents tool."
        )

    # Generate answer via LLM
    try:
        from langchain_litellm import ChatLiteLLM  # type: ignore
        from langchain_core.messages import HumanMessage
        import os
        model = os.environ.get("AICORE_DEPLOYMENT_ID", "gpt-4o")
        llm = ChatLiteLLM(model=model, temperature=0.0)
        prompt = build_rag_prompt(question, results)
        response = llm.invoke([HumanMessage(content=prompt)])
        llm_text = response.content
    except Exception as exc:
        logger.warning("LLM call failed in query tool (%s) — returning raw chunks", exc)
        llm_text = "\n\n".join(
            f"[{c.source_doc} / {c.section}]: {c.text}" for c, _ in results
        )

    rag_answer = format_rag_answer(llm_text, results)

    logger.info(
        "M3.achieved: Q&A response generated — rollout %s, query resolved with %d source chunks",
        resolved_name or "all",
        len(results),
    )

    # Format output
    source_lines = "\n".join(
        f"  {i+1}. {s['document']} › {s['section']} (relevance: {s['relevance']})"
        for i, s in enumerate(rag_answer.sources)
    )
    return f"{rag_answer.answer}\n\n**Sources:**\n{source_lines}"
