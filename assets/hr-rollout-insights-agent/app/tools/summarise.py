"""Summarisation tools — summarise individual documents or full rollout initiatives."""

import logging
from typing import Optional

from langchain_core.tools import tool

from ingestion.vector_store import get_vector_store
from utils.rollout_resolver import resolve_rollout_name
from registry import get_registry

logger = logging.getLogger(__name__)


def _call_llm(prompt: str) -> str:
    """Call the LLM and return response text."""
    try:
        from langchain_litellm import ChatLiteLLM  # type: ignore
        from langchain_core.messages import HumanMessage
        import os
        model = os.environ.get("AICORE_DEPLOYMENT_ID", "gpt-4o")
        llm = ChatLiteLLM(model=model, temperature=0.0)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as exc:
        logger.warning("LLM call failed in summarise tool: %s", exc)
        return ""


@tool
def summarise_document(document_name: str, rollout_name: str) -> str:
    """Summarise a specific document from a rollout initiative.

    Provides a concise summary of the document's key points, scope, and decisions.

    Args:
        document_name: The filename of the document to summarise (e.g., 'project_plan.md').
        rollout_name: The rollout initiative the document belongs to.

    Returns:
        A concise summary of the document with source reference.
    """
    store = get_vector_store()
    chunks = store.get_by_doc(document_name, rollout_name)

    if not chunks:
        return (
            f"Document '{document_name}' was not found in rollout '{rollout_name}'. "
            "Ensure the document has been ingested using ingest_documents."
        )

    combined_text = "\n\n".join(c.text for c in chunks)
    prompt = (
        f"Summarise the following document from an HR rollout in 3-5 concise bullet points. "
        f"Include key decisions, scope, timelines, and action items. "
        f"Document name: {document_name}\n\n{combined_text}"
    )
    summary = _call_llm(prompt)
    if not summary:
        summary = f"Could not generate summary. Document has {len(chunks)} chunk(s) indexed."

    return f"**Summary of '{document_name}' (Rollout: {rollout_name})**\n\n{summary}\n\n*Source: {document_name}*"


@tool
def summarise_rollout(rollout_name: str) -> str:
    """Summarise all documents for a named rollout initiative.

    Synthesises an overview of the rollout covering scope, timeline, open items,
    and key decisions across all indexed documents.

    Args:
        rollout_name: The rollout initiative to summarise.

    Returns:
        A synthesised overview citing contributing documents.
    """
    store = get_vector_store()
    registry = get_registry()

    resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
    if resolved is None:
        return (
            f"No rollout initiative matching '{rollout_name}' was found. "
            f"Available: {', '.join(registry.all_names()) or 'none'}."
        )
    if not is_exact:
        rollout_name = resolved

    chunks = store.get_by_rollout(rollout_name)
    if not chunks:
        return (
            f"No documents have been indexed for rollout '{rollout_name}'. "
            "Use ingest_documents to load documents first."
        )

    # Sample up to 20 chunks across document types for a representative overview
    from collections import defaultdict
    by_doc: dict = defaultdict(list)
    for c in chunks:
        by_doc[c.source_doc].append(c)

    sampled = []
    for doc_chunks in by_doc.values():
        sampled.extend(doc_chunks[:3])

    combined = "\n\n".join(f"[{c.source_doc}]: {c.text}" for c in sampled[:20])
    doc_list = ", ".join(by_doc.keys())

    prompt = (
        f"You are reviewing HR rollout documents for the initiative '{rollout_name}'. "
        f"Synthesise an overview covering: scope and objectives, key timeline milestones, "
        f"open items or risks, and key decisions made. "
        f"Cite the contributing document name for each point.\n\n{combined}"
    )
    summary = _call_llm(prompt)
    if not summary:
        summary = f"Could not generate summary. {len(chunks)} chunks indexed across {len(by_doc)} document(s)."

    return (
        f"**Rollout Overview: {rollout_name}**\n\n{summary}\n\n"
        f"*Contributing documents: {doc_list}*"
    )
