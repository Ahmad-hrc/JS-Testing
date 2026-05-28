"""Document ingestion tool — fetches, chunks, embeds and indexes rollout documents."""

import logging
import os
from typing import Optional

from langchain_core.tools import tool

from ingestion.chunker import chunk_text
from ingestion.embedder import embed_texts
from ingestion.vector_store import Chunk, get_vector_store
from registry import DocumentSource, get_registry

logger = logging.getLogger(__name__)


def _get_connector(source: DocumentSource):
    """Return the appropriate connector for a document source."""
    if source.type == "sharepoint":
        from connectors.sharepoint import SharePointConnector
        return SharePointConnector(source.connection)
    # default: local file
    from connectors.local_file import LocalFileConnector
    folder = source.connection.get("folder_path", ".")
    return LocalFileConnector(folder)


@tool
def ingest_documents(rollout_name: str, folder_path: Optional[str] = None) -> str:
    """Ingest and index documents for a named rollout initiative.

    Use this tool to load documents from the configured document sources for a rollout
    so they become available for Q&A, summarisation, and analysis.

    Args:
        rollout_name: The name of the rollout initiative (e.g., 'SuccessFactors Onboarding Q4').
        folder_path: Optional local folder path override for development/testing.

    Returns:
        A summary of how many documents were ingested and indexed.
    """
    registry = get_registry()
    store = get_vector_store()

    initiative = registry.get(rollout_name)
    if initiative is None and folder_path:
        # Allow ad-hoc ingestion from a folder for dev/test
        from connectors.local_file import LocalFileConnector
        connector = LocalFileConnector(folder_path)
        sources_to_process = [(connector, "unknown")]
    elif initiative is None:
        logger.warning("M1.missed: document ingestion did not complete for rollout %s — initiative not registered", rollout_name)
        return (
            f"Rollout initiative '{rollout_name}' is not registered. "
            "Please configure it in rollout_config.yaml or provide a folder_path."
        )
    else:
        sources_to_process = [(_get_connector(s), s.doc_type_hints[0] if s.doc_type_hints else "unknown") for s in initiative.sources]

    total_docs = 0
    total_chunks = 0

    for connector, default_doc_type in sources_to_process:
        try:
            documents = connector.fetch_all()
        except Exception as exc:
            source_label = getattr(connector, "folder_path", getattr(connector, "site_url", "unknown"))
            logger.error("M1.missed: document ingestion did not complete for rollout %s — source: %s — error: %s", rollout_name, source_label, exc)
            continue

        for doc_name, content in documents:
            if not content.strip():
                continue
            doc_type = _infer_doc_type(doc_name, default_doc_type)
            raw_chunks = chunk_text(content, source_doc=doc_name, doc_type=doc_type)
            if not raw_chunks:
                continue

            texts = [c["text"] for c in raw_chunks]
            embeddings = embed_texts(texts)

            chunks = [
                Chunk(
                    text=rc["text"],
                    source_doc=rc["source_doc"],
                    section=rc["section"],
                    rollout_name=rollout_name,
                    doc_type=rc["doc_type"],
                    embedding=emb,
                )
                for rc, emb in zip(raw_chunks, embeddings)
            ]
            store.upsert(chunks, rollout_name)
            total_docs += 1
            total_chunks += len(chunks)

    registry.update_doc_count(rollout_name, total_docs)

    if total_docs > 0:
        logger.info(
            "M2.achieved: rollout context established — initiative %s mapped to %d documents",
            rollout_name,
            total_docs,
        )
    else:
        logger.warning(
            "M2.missed: rollout context not established — initiative %s has no indexed documents",
            rollout_name,
        )

    if total_docs == 0:
        logger.warning("M1.missed: document ingestion did not complete for rollout %s — no documents found", rollout_name)
        return f"No documents were found for rollout '{rollout_name}'. Please check the source configuration."

    logger.info("M1.achieved: document ingestion completed — %d documents indexed for rollout %s", total_docs, rollout_name)
    return (
        f"Successfully ingested {total_docs} document(s) ({total_chunks} chunks) "
        f"for rollout initiative '{rollout_name}'."
    )


def _infer_doc_type(doc_name: str, default: str) -> str:
    """Infer document type from filename."""
    name_lower = doc_name.lower()
    if any(k in name_lower for k in ["project_plan", "project plan", "timeline", "workplan"]):
        return "project_plan"
    if any(k in name_lower for k in ["training", "learning", "course", "workshop"]):
        return "training_material"
    if any(k in name_lower for k in ["change", "ocm", "stakeholder", "impact"]):
        return "change_management"
    if any(k in name_lower for k in ["comms", "communication", "announcement", "newsletter"]):
        return "comms_plan"
    if any(k in name_lower for k in ["go_live", "go-live", "golive", "readiness", "checklist"]):
        return "go_live_checklist"
    if any(k in name_lower for k in ["risk", "issue", "constraint"]):
        return "risk_register"
    return default
