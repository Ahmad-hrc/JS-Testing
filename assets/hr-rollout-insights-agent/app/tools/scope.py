"""Scope tool — lists registered rollout initiatives."""

import logging

from langchain_core.tools import tool

from registry import get_registry

logger = logging.getLogger(__name__)


@tool
def list_rollout_initiatives() -> str:
    """List all registered HR rollout initiatives and their document counts.

    Use this tool to show the user what rollout initiatives are available
    before querying or summarising documents.

    Returns:
        A formatted list of initiative names and document counts.
    """
    registry = get_registry()
    names = registry.all_names()
    if not names:
        return (
            "No rollout initiatives are currently registered. "
            "Use the ingest_documents tool to load documents for a rollout initiative."
        )
    lines = ["Available rollout initiatives:"]
    for name in names:
        initiative = registry.get(name)
        doc_count = initiative.doc_count if initiative else 0
        lines.append(f"  • {name} ({doc_count} document(s) indexed)")
    return "\n".join(lines)
