"""Integration test — end-to-end agent flow with mocked LLM and local documents."""

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("IBD_TESTING", "1")

SAMPLE_DOC = """# SuccessFactors Onboarding Go-Live Checklist

## Go-Live Readiness Criteria

All of the following must be completed before go-live:
- System configuration validated by IT
- User acceptance testing (UAT) sign-off obtained from HR Director
- All employees enrolled in mandatory onboarding training
- Communication sent to all managers

## Open Items

Action: Complete manager briefing sessions. Owner: Miriam HR. Due: 2025-11-20. Status: Open.
Action: Finalize system access matrix. Owner: IT Team. Due: 2025-11-15. Status: Open.

## Risks

Risk: Training platform downtime during go-live week. Status: Open. Mitigation: Backup e-learning links prepared.
"""

SAMPLE_PROJECT_PLAN = """# SuccessFactors Onboarding Project Plan Q4-2025

## Milestones

Milestone 1: System configuration complete. Status: Done. Completed: 2025-10-15.
Milestone 2: UAT complete. Status: In Progress. Due: 2025-11-10.
Milestone 3: Go-live. Status: Not Started. Due: 2025-12-01.

## Timeline

Phase 1 (Oct): Configuration
Phase 2 (Nov): Testing and training
Phase 3 (Dec): Go-live and hypercare
"""


@pytest.fixture
def sample_rollout_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "go_live_checklist.txt"), "w") as f:
            f.write(SAMPLE_DOC)
        with open(os.path.join(tmpdir, "project_plan.txt"), "w") as f:
            f.write(SAMPLE_PROJECT_PLAN)
        yield tmpdir


@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_ingest_and_query(sample_rollout_folder):
    """End-to-end: ingest local docs, query for go-live criteria, verify source-cited answer."""
    from ingestion.vector_store import VectorStore, reset_vector_store
    from registry import RolloutRegistry, reset_registry

    reset_vector_store()
    reset_registry()

    # Pre-register rollout initiative so query tool can resolve its name
    from registry import get_registry, RolloutInitiative, DocumentSource
    registry = get_registry()
    registry.register(RolloutInitiative(
        name="SF Onboarding Q4",
        sources=[DocumentSource(type="local", connection={"folder_path": sample_rollout_folder})],
    ))

    # Step 1: Ingest documents
    with patch("tools.ingest.embed_texts", return_value=[[float(i % 10) / 10] * 1536 for i in range(20)]):
        from tools.ingest import ingest_documents
        ingest_result = ingest_documents.invoke({
            "rollout_name": "SF Onboarding Q4",
        })

    assert "Successfully ingested" in ingest_result
    assert "SF Onboarding Q4" in ingest_result

    # Step 2: Check rollout is listed
    from tools.scope import list_rollout_initiatives
    scope_result = list_rollout_initiatives.invoke({})
    # Registry is empty here since we used ad-hoc folder_path (no registry entry)
    # but the vector store should have indexed the documents
    from ingestion.vector_store import get_vector_store
    store = get_vector_store()
    assert store.count("SF Onboarding Q4") > 0

    # Step 3: Query — mock the embedding and LLM
    mock_llm_response = MagicMock()
    mock_llm_response.content = (
        "Go-live readiness criteria include: system configuration validated, "
        "UAT sign-off from HR Director, all employees enrolled in mandatory onboarding training, "
        "and communication sent to all managers. "
        "[go_live_checklist.txt / Go-Live Readiness Criteria]"
    )

    with patch("tools.query.embed_query", return_value=[0.9] * 1536), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm_class:

        mock_llm_class.return_value.invoke.return_value = mock_llm_response

        from tools.query import query_rollout_documents
        query_result = query_rollout_documents.invoke({
            "question": "What are the go-live readiness criteria?",
            "rollout_name": "SF Onboarding Q4",
        })

    # Verify: answer contains source citations, not fabricated content
    assert "Sources:" in query_result
    assert "go_live_checklist.txt" in query_result
    # Should not say "no documents found" since we ingested docs
    assert "No relevant documents" not in query_result

    # Step 4: Gap analysis — seed store with enough chunks to pass threshold
    from ingestion.vector_store import VectorStore, Chunk as VChunk
    gap_store = VectorStore()
    bulk_chunks = [
        VChunk(
            text=f"Project plan content chunk {i}",
            source_doc=f"doc_{i}.txt",
            section="Section",
            rollout_name="SF Onboarding Q4",
            doc_type="project_plan",
            embedding=[0.5] * 1536,
        )
        for i in range(5)
    ]
    gap_store.upsert(bulk_chunks, "SF Onboarding Q4")

    mock_gap_response = MagicMock()
    mock_gap_response.content = "Communications plan document not found in corpus."

    with patch("tools.gap_analysis.get_vector_store", return_value=gap_store), \
         patch("tools.gap_analysis.get_registry", return_value=registry), \
         patch("langchain_litellm.ChatLiteLLM") as mock_llm_gap:

        mock_llm_gap.return_value.invoke.return_value = mock_gap_response

        from tools.gap_analysis import identify_gaps
        gap_result = identify_gaps.invoke({"rollout_name": "SF Onboarding Q4"})

    assert "Gap Analysis" in gap_result
    # training_material and comms_plan are missing from our sample corpus
    assert "Training" in gap_result or "Communications" in gap_result
