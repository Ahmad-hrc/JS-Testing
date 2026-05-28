"""Unit tests for get_rollout_status and get_open_actions tools."""

import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("IBD_TESTING", "1")


def _seed_status_chunks(store, rollout_name: str):
    from ingestion.vector_store import Chunk
    chunks = [
        Chunk(
            text="Milestone 1: Configuration complete. Milestone 2: UAT in progress (due Dec 5).",
            source_doc="project_plan.txt",
            section="Milestones",
            rollout_name=rollout_name,
            doc_type="project_plan",
            embedding=[0.7] * 1536,
        ),
        Chunk(
            text="Action: Finalize training materials. Owner: Sarah Johnson. Due: Nov 20. Status: Open.",
            source_doc="change_management.txt",
            section="Open Items",
            rollout_name=rollout_name,
            doc_type="change_management",
            embedding=[0.6] * 1536,
        ),
    ]
    store.upsert(chunks, rollout_name)


def test_get_rollout_status_emits_m4_achieved(caplog):
    """get_rollout_status returns milestone list and emits M4.achieved."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.status import get_rollout_status

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Status Test Rollout"))
    _seed_status_chunks(store, "Status Test Rollout")

    mock_response = MagicMock()
    mock_response.content = "Completed: Configuration. Open: UAT (Dec 5). No overdue items."

    with patch("tools.status.get_vector_store", return_value=store), \
         patch("tools.status.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response

        with caplog.at_level(logging.INFO):
            result = get_rollout_status.invoke({"rollout_name": "Status Test Rollout"})

    assert "Status Test Rollout" in result
    assert "Sources:" in result or "project_plan" in result
    assert any("M4.achieved" in r.message for r in caplog.records)


def test_get_rollout_status_no_docs_emits_m4_missed(caplog):
    """get_rollout_status emits M4.missed when no relevant docs are found."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.status import get_rollout_status

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Empty Status Rollout"))

    with patch("tools.status.get_vector_store", return_value=store), \
         patch("tools.status.get_registry", return_value=registry):

        with caplog.at_level(logging.WARNING):
            result = get_rollout_status.invoke({"rollout_name": "Empty Status Rollout"})

    assert "No project plan" in result or "Ingest" in result
    assert any("M4.missed" in r.message for r in caplog.records)


def test_get_open_actions_returns_structured_output():
    """get_open_actions returns a list of action items with source citations."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.status import get_open_actions

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Action Rollout"))
    _seed_status_chunks(store, "Action Rollout")

    mock_response = MagicMock()
    mock_response.content = "• Finalize training materials — Owner: Sarah Johnson — Due: Nov 20 — Open [change_management.txt]"

    with patch("tools.status.get_vector_store", return_value=store), \
         patch("tools.status.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response
        result = get_open_actions.invoke({"rollout_name": "Action Rollout"})

    assert "Action Rollout" in result
    assert "Sources:" in result or "change_management" in result
