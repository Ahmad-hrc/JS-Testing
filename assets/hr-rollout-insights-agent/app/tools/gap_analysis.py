"""Gap and risk identification tools for HR rollout document analysis."""

import logging

from langchain_core.tools import tool

from ingestion.vector_store import get_vector_store
from registry import EXPECTED_DOC_TYPES, get_registry
from utils.rollout_resolver import resolve_rollout_name

logger = logging.getLogger(__name__)

RISK_KEYWORDS = ["risk", "issue", "constraint", "blocker", "dependency", "concern", "assumption", "mitigation"]

DOC_TYPE_LABELS = {
    "project_plan": "Project Plan / Timeline",
    "training_material": "Training / Learning Materials",
    "change_management": "Change Management Plan",
    "comms_plan": "Communications Plan",
    "go_live_checklist": "Go-Live Readiness Checklist",
}


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
        logger.warning("LLM call failed in gap_analysis tool: %s", exc)
        return ""


@tool
def identify_gaps(rollout_name: str) -> str:
    """Identify documentation gaps for a rollout initiative.

    Analyses the indexed document corpus against an expected coverage checklist
    (project plan, training materials, change management plan, comms plan, go-live checklist).
    Reports missing document types and undocumented process areas.

    This tool surfaces observations only — all remediation decisions are left to the user.

    Args:
        rollout_name: The rollout initiative to analyse for gaps.

    Returns:
        A structured gap report listing missing document types and undocumented areas.
    """
    registry = get_registry()
    resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
    if resolved is None:
        return f"Rollout initiative '{rollout_name}' not found. Available: {', '.join(registry.all_names()) or 'none'}."
    if not is_exact:
        rollout_name = resolved

    store = get_vector_store()
    chunks = store.get_by_rollout(rollout_name)

    if len(chunks) < 3:
        logger.warning("M5.missed: gap and risk analysis did not complete — insufficient document coverage for rollout %s", rollout_name)
        return (
            f"Insufficient document coverage for rollout '{rollout_name}' — only {len(chunks)} chunk(s) indexed. "
            "Please ingest more documents before running gap analysis."
        )

    present_types = store.doc_types_present(rollout_name)
    missing_types = [t for t in EXPECTED_DOC_TYPES if t not in present_types]

    # LLM-based gap analysis from content
    context = "\n\n".join(f"[{c.source_doc}]: {c.text}" for c in chunks[:15])
    prompt = (
        f"Review the following HR rollout documents for '{rollout_name}' and identify:\n"
        "1. Process areas or topics that appear undocumented or incomplete\n"
        "2. Missing decision records or approvals\n"
        "3. Scope items mentioned but not elaborated\n"
        "Present findings as observations only. Do not recommend actions.\n\n"
        f"{context}"
    )
    llm_gaps = _call_llm(prompt)

    # Build gap report
    report_lines = [f"**Gap Analysis: {rollout_name}**\n"]

    if missing_types:
        report_lines.append("**Missing Document Types:**")
        for t in missing_types:
            report_lines.append(f"  ⚠️ {DOC_TYPE_LABELS.get(t, t)} — not found in indexed documents")
    else:
        report_lines.append("✅ All expected document types are present.")

    if llm_gaps:
        report_lines.append(f"\n**Content Gaps Identified:**\n{llm_gaps}")

    gap_count = len(missing_types)
    docs_present = list({c.source_doc for c in chunks})
    logger.info(
        "M5.achieved: gap and risk analysis completed — %d gaps and content gaps identified for rollout %s",
        gap_count,
        rollout_name,
    )

    report_lines.append(f"\n*Analysis based on {len(chunks)} chunks from: {', '.join(docs_present)}*")
    return "\n".join(report_lines)


@tool
def identify_risks(rollout_name: str) -> str:
    """Identify open risks and issues from rollout documents.

    Extracts risks, blockers, and constraints from risk registers, issue logs,
    and other rollout artefacts. Presents findings as observations only.

    Args:
        rollout_name: The rollout initiative to analyse for risks.

    Returns:
        A structured list of open risks with status and source citations.
    """
    registry = get_registry()
    resolved, is_exact = resolve_rollout_name(rollout_name, registry.all_names())
    if resolved is None:
        return f"Rollout initiative '{rollout_name}' not found. Available: {', '.join(registry.all_names()) or 'none'}."
    if not is_exact:
        rollout_name = resolved

    store = get_vector_store()
    all_chunks = store.get_by_rollout(rollout_name)
    risk_chunks = [
        c for c in all_chunks
        if any(kw in c.text.lower() for kw in RISK_KEYWORDS)
        or c.doc_type == "risk_register"
    ]

    if not risk_chunks:
        if not all_chunks:
            return f"No documents indexed for rollout '{rollout_name}'. Use ingest_documents first."
        risk_chunks = all_chunks[:10]

    context = "\n\n".join(f"[{c.source_doc}]: {c.text}" for c in risk_chunks[:15])
    prompt = (
        f"From the following HR rollout documents for '{rollout_name}', extract all risks, issues, and blockers. "
        "For each, provide: description, status (open/mitigated/accepted), owner (if known). "
        "Present findings as observations only. Format as structured bullet list with source citations.\n\n"
        f"{context}"
    )
    result = _call_llm(prompt)
    if not result:
        result = f"Risk data from {len(risk_chunks)} chunk(s). Manual review of source documents recommended."

    doc_list = list({c.source_doc for c in risk_chunks})
    risk_count = len(risk_chunks)
    logger.info(
        "M5.achieved: gap and risk analysis completed — %d risks identified for rollout %s",
        risk_count,
        rollout_name,
    )
    return f"**Risk Register: {rollout_name}**\n\n{result}\n\n*Sources: {', '.join(doc_list)}*"
