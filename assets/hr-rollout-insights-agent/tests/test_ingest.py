"""Unit tests for the ingest_documents tool."""

import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

os.environ.setdefault("IBD_TESTING", "true")


def _make_store_and_registry():
    """Return fresh (store, registry) singletons for each test."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative, DocumentSource

    store = VectorStore()
    registry = RolloutRegistry()
    initiative = RolloutInitiative(
        name="Test Rollout",
        sources=[DocumentSource(type="local", connection={"folder_path": "."})],
    )
    registry.register(initiative)
    return store, registry


def _write_sample_doc(folder: str, filename: str, content: str):
    path = os.path.join(folder, filename)
    with open(path, "w") as f:
        f.write(content)
    return path


def test_ingest_documents_happy_path(caplog):
    """Ingesting a folder with documents indexes chunks and emits M1.achieved."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative, DocumentSource

    with tempfile.TemporaryDirectory() as tmpdir:
        _write_sample_doc(tmpdir, "project_plan.txt", "# Project Plan\n\nMilestone 1: Complete by Jan\n\nMilestone 2: Testing in Feb")

        store = VectorStore()
        registry = RolloutRegistry()
        registry.register(RolloutInitiative(
            name="Test Rollout",
            sources=[DocumentSource(type="local", connection={"folder_path": tmpdir})],
        ))

        with patch("tools.ingest.get_vector_store", return_value=store), \
             patch("tools.ingest.get_registry", return_value=registry), \
             patch("tools.ingest.embed_texts", return_value=[[0.1] * 1536]):

            with caplog.at_level(logging.INFO):
                result = ingest_documents.invoke({"rollout_name": "Test Rollout"})

    assert "Successfully ingested" in result
    assert "Test Rollout" in result
    assert store.count("Test Rollout") > 0
    assert any("M1.achieved" in r.message for r in caplog.records)


def test_ingest_documents_unknown_initiative():
    """Ingesting an unknown initiative with no folder_path returns error and emits M1.missed."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry

    store = VectorStore()
    registry = RolloutRegistry()

    with patch("tools.ingest.get_vector_store", return_value=store), \
         patch("tools.ingest.get_registry", return_value=registry):

        result = ingest_documents.invoke({"rollout_name": "Unknown Rollout"})

    assert "not registered" in result


def test_ingest_documents_with_folder_override():
    """Ingesting with folder_path override works for ad-hoc ingestion."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry

    with tempfile.TemporaryDirectory() as tmpdir:
        _write_sample_doc(tmpdir, "comms_plan.txt", "Communications Plan\n\nAll employees will be notified.")

        store = VectorStore()
        registry = RolloutRegistry()

        with patch("tools.ingest.get_vector_store", return_value=store), \
             patch("tools.ingest.get_registry", return_value=registry), \
             patch("tools.ingest.embed_texts", return_value=[[0.2] * 1536]):

            result = ingest_documents.invoke({"rollout_name": "Ad-hoc Rollout", "folder_path": tmpdir})

    assert "Successfully ingested" in result
    assert store.count("Ad-hoc Rollout") > 0


def test_ingest_empty_folder(caplog):
    """Ingesting from an empty folder emits M1.missed."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative, DocumentSource

    with tempfile.TemporaryDirectory() as tmpdir:
        store = VectorStore()
        registry = RolloutRegistry()
        registry.register(RolloutInitiative(
            name="Empty Rollout",
            sources=[DocumentSource(type="local", connection={"folder_path": tmpdir})],
        ))

        with patch("tools.ingest.get_vector_store", return_value=store), \
             patch("tools.ingest.get_registry", return_value=registry):

            with caplog.at_level(logging.WARNING):
                result = ingest_documents.invoke({"rollout_name": "Empty Rollout"})

    assert "No documents" in result
    assert any("M1.missed" in r.message for r in caplog.records)


# Import after patching setup
from tools.ingest import ingest_documents
