"""Rollout status and milestone tracking tools."""

import logging

from langchain_core.tools import tool

from ingestion.vector_store import get_vector_store
from utils.rollout_resolver import resolve_rollout_name
from registry import get_registry

logger = logging.getLogger(__name__)

STATUS_KEYWORDS = ["milestone", "complete", "done", "in progress", "overdue", "pending", "phase", "go-live", "deadline"]
ACTION_KEYWORDS = ["action", "open item", "to do", "todo", "owner", "due date", "assigned", "responsible", "follow-up"]


def _call_llm(prompt: str) -> str:
    try:
        from langchain_litellm import ChatLiteLLM  # type: ignore
        from langchain_core.messages import HumanMessage
        import os
        model = os.environ.get("AICORE_DEPLOYMENT_ID", "gpt-4o")
        llm = ChatLiteLLM(model=model, temperature=0.0)
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content
    except Exception as exc:
        logger.warning("LLM call failed in status tool: %s", exc)
        return ""


def _get_status_chunks(rollout_name: str):
    """Get chunks likely containing milestone/status content."""
    store = get_vector_store()
    chunks = store.get_by_rollout(rollout_name)
    relevant = [
        c for c in chunks
        if any(kw in c.text.lower() for kw in STATUS_KEYWORDS)
        or c.doc_type in ("project_plan", "go_live_checklist")
    ]
    return relevant or chunks[:10]


def _get_action_chunks(rollout_name: str):
    """Get chunks likely containing action items."""
    store = get_vector_store()
    chunks = store.get_by_rollout(rollout_name)
    relevant = [
        c for c in chunks
        if any(kw in c.text.lower() for kw in ACTION_KEYWORDS)
        or c.doc_type in ("change_management", "comms_plan", "project_plan")
    ]
    return relevant or chunks[:10]


@tool
def get_rollout_status(rollout_name: str) -> str:
    """Get milestone status and progress for a rollout initiative.

    Extracts completed milestones, open milestones, and overdue items
    from project plan and change management documents.

    Args:
        rollout_name: The rollout initiative to check status for.

    Returns:
        A structured list of milestones (completed, open, overdue) with source citations.
    """
    registry = get_registry()
    resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
    if resolved is None:
        return f"Rollout initiative '{rollout_name}' not found. Available: {', '.join(registry.all_names()) or 'none'}."
    if not is_exact:
        rollout_name = resolved

    chunks = _get_status_chunks(rollout_name)
    if not chunks:
        logger.warning("M4.missed: status tracking incomplete — no project plan or change management documents found for rollout %s", rollout_name)
        return (
            f"No project plan or change management documents found for rollout '{rollout_name}'. "
            "Ingest documents first using ingest_documents."
        )

    context = "\n\n".join(f"[{c.source_doc}]: {c.text}" for c in chunks[:15])
    prompt = (
        f"From the following HR rollout documents for '{rollout_name}', extract:\n"
        "1. Completed milestones (with dates if available)\n"
        "2. Open/pending milestones (with target dates if available)\n"
        "3. Overdue items\n"
        "For each item, cite the source document. Format as structured bullet lists.\n\n"
        f"{context}"
    )
    result = _call_llm(prompt)
    if not result:
        result = f"Status data extracted from {len(chunks)} chunk(s). Manual review of source documents recommended."

    doc_list = list({c.source_doc for c in chunks})
    milestone_count = len(chunks)
    logger.info(
        "M4.achieved: status tracking completed — %d milestones and open items surfaced for rollout %s",
        milestone_count,
        rollout_name,
    )
    return f"**Rollout Status: {rollout_name}**\n\n{result}\n\n*Sources: {', '.join(doc_list)}*"


@tool
def get_open_actions(rollout_name: str) -> str:
    """Get open action items and owners for a rollout initiative.

    Extracts action items, owners, and due dates from change management
    and communication documents.

    Args:
        rollout_name: The rollout initiative to retrieve open actions for.

    Returns:
        A structured list of open actions with owners, due dates, and source citations.
    """
    registry = get_registry()
    resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
    if resolved is None:
        return f"Rollout initiative '{rollout_name}' not found. Available: {', '.join(registry.all_names()) or 'none'}."
    if not is_exact:
        rollout_name = resolved

    chunks = _get_action_chunks(rollout_name)
    if not chunks:
        return f"No action item documents found for rollout '{rollout_name}'."

    context = "\n\n".join(f"[{c.source_doc}]: {c.text}" for c in chunks[:15])
    prompt = (
        f"From the following HR rollout documents for '{rollout_name}', extract all open action items. "
        "For each, provide: action description, owner (if mentioned), due date (if mentioned), status. "
        "Format as a structured bullet list with source citations.\n\n"
        f"{context}"
    )
    result = _call_llm(prompt)
    if not result:
        result = f"Action items from {len(chunks)} chunk(s). Manual review recommended."

    doc_list = list({c.source_doc for c in chunks})
    return f"**Open Actions: {rollout_name}**\n\n{result}\n\n*Sources: {', '.join(doc_list)}*"
