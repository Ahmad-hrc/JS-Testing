"""Unit tests for query_rollout_documents tool."""

import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("IBD_TESTING", "1")


def _seed_store(store, rollout_name: str):
    """Seed the vector store with sample chunks."""
    from ingestion.vector_store import Chunk
    chunks = [
        Chunk(
            text="Go-live readiness criteria: all training completed, sign-off from HR Director obtained.",
            source_doc="go_live_checklist.txt",
            section="Readiness Criteria",
            rollout_name=rollout_name,
            doc_type="go_live_checklist",
            embedding=[0.9] * 1536,
        ),
        Chunk(
            text="Phase 1 milestone: System configured and tested by March 15.",
            source_doc="project_plan.txt",
            section="Phase 1",
            rollout_name=rollout_name,
            doc_type="project_plan",
            embedding=[0.8] * 1536,
        ),
    ]
    store.upsert(chunks, rollout_name)
    return chunks


def test_query_returns_source_citations(caplog):
    """query_rollout_documents returns answer with source citations and emits M3.achieved."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Onboarding Q4"))
    _seed_store(store, "Onboarding Q4")

    mock_llm_response = MagicMock()
    mock_llm_response.content = "Training must be completed and HR Director sign-off obtained. [go_live_checklist.txt / Readiness Criteria]"

    with patch("tools.query.get_vector_store", return_value=store), \
         patch("tools.query.get_registry", return_value=registry), \
         patch("tools.query.embed_query", return_value=[0.85] * 1536), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm_class:

        mock_llm_class.return_value.invoke.return_value = mock_llm_response

        with caplog.at_level(logging.INFO):
            from tools.query import query_rollout_documents
            result = query_rollout_documents.invoke({
                "question": "What are the go-live readiness criteria?",
                "rollout_name": "Onboarding Q4",
            })

    assert "Sources:" in result
    assert "go_live_checklist.txt" in result
    assert any("M3.achieved" in r.message for r in caplog.records)


def test_query_no_documents_emits_m3_missed(caplog):
    """When no documents are found, M3.missed is emitted."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Empty Rollout"))

    with patch("tools.query.get_vector_store", return_value=store), \
         patch("tools.query.get_registry", return_value=registry), \
         patch("tools.query.embed_query", return_value=[0.5] * 1536):

        with caplog.at_level(logging.WARNING):
            from tools.query import query_rollout_documents
            result = query_rollout_documents.invoke({
                "question": "What is the timeline?",
                "rollout_name": "Empty Rollout",
            })

    assert "No relevant documents" in result
    assert any("M3.missed" in r.message for r in caplog.records)


def test_query_unknown_rollout_returns_error():
    """Querying an unknown rollout returns helpful error message."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry

    store = VectorStore()
    registry = RolloutRegistry()

    with patch("tools.query.get_vector_store", return_value=store), \
         patch("tools.query.get_registry", return_value=registry), \
         patch("tools.query.embed_query", return_value=[0.5] * 1536):

        from tools.query import query_rollout_documents
        result = query_rollout_documents.invoke({
            "question": "What is the timeline?",
            "rollout_name": "Non-existent Rollout",
        })

    assert "not found" in result.lower() or "No relevant" in result or "was found" in result


def test_query_cross_rollout_no_scope():
    """Querying without rollout scope searches all indexed documents."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Rollout A"))
    _seed_store(store, "Rollout A")

    mock_response = MagicMock()
    mock_response.content = "Found relevant information across all rollouts."

    with patch("tools.query.get_vector_store", return_value=store), \
         patch("tools.query.get_registry", return_value=registry), \
         patch("tools.query.embed_query", return_value=[0.85] * 1536), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response

        from tools.query import query_rollout_documents
        result = query_rollout_documents.invoke({
            "question": "What milestones exist?",
        })

    assert "Sources:" in result
