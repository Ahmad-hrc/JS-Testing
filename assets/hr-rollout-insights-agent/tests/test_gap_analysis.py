"""Unit tests for identify_gaps and identify_risks tools."""

import os
from unittest.mock import patch, MagicMock

import pytest

os.environ.setdefault("IBD_TESTING", "1")


def _seed_partial_corpus(store, rollout_name: str):
    """Seed store with only project_plan — missing training_material, comms_plan, etc."""
    from ingestion.vector_store import Chunk
    chunks = [
        Chunk(
            text="Project plan: Go-live scheduled for Q4. Configuration to be completed by Nov 1.",
            source_doc="project_plan.txt",
            section="Overview",
            rollout_name=rollout_name,
            doc_type="project_plan",
            embedding=[0.5] * 1536,
        ),
        Chunk(
            text="Risk: Dependency on IT team resource availability. Status: Open. Mitigation: escalate.",
            source_doc="risk_register.txt",
            section="Risks",
            rollout_name=rollout_name,
            doc_type="risk_register",
            embedding=[0.4] * 1536,
        ),
        Chunk(
            text="Blocker: Legacy system integration not yet signed off. Owner: IT Director.",
            source_doc="risk_register.txt",
            section="Blockers",
            rollout_name=rollout_name,
            doc_type="risk_register",
            embedding=[0.45] * 1536,
        ),
    ]
    store.upsert(chunks, rollout_name)


def test_identify_gaps_flags_missing_doc_types(caplog):
    """identify_gaps reports missing training_material and emits M5.achieved."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.gap_analysis import identify_gaps

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Gap Test Rollout"))
    _seed_partial_corpus(store, "Gap Test Rollout")

    mock_response = MagicMock()
    mock_response.content = "Training objectives are mentioned but no training plan document was found."

    with patch("tools.gap_analysis.get_vector_store", return_value=store), \
         patch("tools.gap_analysis.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response

        with caplog.at_level(logging.INFO):
            result = identify_gaps.invoke({"rollout_name": "Gap Test Rollout"})

    # Should flag missing training_material, change_management, comms_plan, go_live_checklist
    assert "Training" in result or "training_material" in result
    assert "Gap Analysis" in result
    assert any("M5.achieved" in r.message for r in caplog.records)


def test_identify_gaps_insufficient_corpus_emits_m5_missed(caplog):
    """identify_gaps emits M5.missed when corpus is too thin (< 3 chunks)."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.gap_analysis import identify_gaps

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Thin Rollout"))
    # Only 1 chunk
    from ingestion.vector_store import Chunk
    store.upsert([Chunk(
        text="One small document.",
        source_doc="a.txt",
        section="All",
        rollout_name="Thin Rollout",
        doc_type="project_plan",
        embedding=[0.3] * 1536,
    )], "Thin Rollout")

    with patch("tools.gap_analysis.get_vector_store", return_value=store), \
         patch("tools.gap_analysis.get_registry", return_value=registry):

        with caplog.at_level(logging.WARNING):
            result = identify_gaps.invoke({"rollout_name": "Thin Rollout"})

    assert "Insufficient" in result or "insufficient" in result
    assert any("M5.missed" in r.message for r in caplog.records)


def test_identify_risks_returns_structured_list(caplog):
    """identify_risks returns risk list with source citations and emits M5.achieved."""
    import logging
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative
    from tools.gap_analysis import identify_risks

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(name="Risk Test Rollout"))
    _seed_partial_corpus(store, "Risk Test Rollout")

    mock_response = MagicMock()
    mock_response.content = "• IT resource dependency — Status: Open — Owner: IT Director [risk_register.txt]"

    with patch("tools.gap_analysis.get_vector_store", return_value=store), \
         patch("tools.gap_analysis.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm:

        mock_llm.return_value.invoke.return_value = mock_response

        with caplog.at_level(logging.INFO):
            result = identify_risks.invoke({"rollout_name": "Risk Test Rollout"})

    assert "Risk Register" in result
    assert "risk_register.txt" in result
    assert any("M5.achieved" in r.message for r in caplog.records)
