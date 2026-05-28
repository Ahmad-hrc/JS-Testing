"""Unit tests for summarise_document and summarise_rollout tools."""

import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("IBD_TESTING", "1")


def _seed_store_with_doc(store, rollout_name: str, doc_name: str, text: str, doc_type: str = "project_plan"):
    from ingestion.vector_store import Chunk
    chunk = Chunk(
        text=text,
        source_doc=doc_name,
        section="Section 1",
        rollout_name=rollout_name,
        doc_type=doc_type,
        embedding=[0.5] * 1536,
    )
    store.upsert([chunk], rollout_name)


def test_summarise_document_returns_summary():
    """summarise_document returns a summary containing the document name."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.summarise import summarise_document

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Test Rollout"))
    _seed_store_with_doc(store, "Test Rollout", "project_plan.txt", "Q4 go-live milestone on Nov 30.")

    mock_response = MagicMock()
    mock_response.content = "• Q4 go-live milestone on Nov 30\n• Key decisions pending stakeholder sign-off"

    with patch("tools.summarise.get_vector_store", return_value=store), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response
        result = summarise_document.invoke({"document_name": "project_plan.txt", "rollout_name": "Test Rollout"})

    assert "project_plan.txt" in result
    assert "Summary" in result
    assert "Test Rollout" in result


def test_summarise_document_not_found():
    """summarise_document returns helpful error for unknown document."""
    from ingestion.vector_store import VectorStore
    from tools.summarise import summarise_document

    store = VectorStore()

    with patch("tools.summarise.get_vector_store", return_value=store):
        result = summarise_document.invoke({"document_name": "missing.txt", "rollout_name": "Any Rollout"})

    assert "not found" in result.lower()


def test_summarise_rollout_returns_overview():
    """summarise_rollout returns a synthesised overview with contributing documents listed."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.summarise import summarise_rollout

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="PnG Rollout"))
    _seed_store_with_doc(store, "PnG Rollout", "project_plan.txt", "Phase 1 complete. Phase 2 in progress.")
    _seed_store_with_doc(store, "PnG Rollout", "comms_plan.txt", "Stakeholder emails sent. Town halls scheduled.", doc_type="comms_plan")

    mock_response = MagicMock()
    mock_response.content = "Rollout is on track. Phase 2 in progress. Communications initiated."

    with patch("tools.summarise.get_vector_store", return_value=store), \
         patch("tools.summarise.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response
        result = summarise_rollout.invoke({"rollout_name": "PnG Rollout"})

    assert "PnG Rollout" in result
    assert "project_plan.txt" in result or "comms_plan.txt" in result


def test_summarise_rollout_no_documents():
    """summarise_rollout returns helpful error when no docs are indexed."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.summarise import summarise_rollout

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Empty Rollout"))

    with patch("tools.summarise.get_vector_store", return_value=store), \
         patch("tools.summarise.get_registry", return_value=registry):

        result = summarise_rollout.invoke({"rollout_name": "Empty Rollout"})

    assert "No documents" in result or "ingest" in result.lower()
