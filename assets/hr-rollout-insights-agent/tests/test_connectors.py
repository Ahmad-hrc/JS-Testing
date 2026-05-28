"""Tests for document connectors and ingest doc-type inference."""

import os
import tempfile
from unittest.mock import patch

import pytest

os.environ.setdefault("IBD_TESTING", "1")


# --- LocalFileConnector ---

def test_local_connector_list_documents():
    from connectors.local_file import LocalFileConnector
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "doc1.txt"), "w").write("text1")
        open(os.path.join(tmpdir, "doc2.md"), "w").write("text2")
        open(os.path.join(tmpdir, "skip.pdf"), "w").write("pdf")  # not supported

        connector = LocalFileConnector(tmpdir)
        docs = connector.list_documents()

    assert any("doc1.txt" in d for d in docs)
    assert any("doc2.md" in d for d in docs)
    assert not any("skip.pdf" in d for d in docs)


def test_local_connector_missing_folder():
    from connectors.local_file import LocalFileConnector
    connector = LocalFileConnector("/nonexistent/folder")
    assert connector.list_documents() == []


def test_local_connector_read_missing_file():
    from connectors.local_file import LocalFileConnector
    connector = LocalFileConnector(".")
    result = connector.read_document("/nonexistent/file.txt")
    assert result == ""


def test_local_connector_fetch_all():
    from connectors.local_file import LocalFileConnector
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "a.txt"), "w").write("content a")
        open(os.path.join(tmpdir, "b.txt"), "w").write("content b")
        connector = LocalFileConnector(tmpdir)
        results = connector.fetch_all()

    assert len(results) == 2
    names = [r[0] for r in results]
    assert "a.txt" in names
    assert "b.txt" in names


# --- Ingest doc_type inference ---

def test_ingest_doc_type_inference():
    from tools.ingest import _infer_doc_type
    assert _infer_doc_type("Q4_project_plan.txt", "unknown") == "project_plan"
    assert _infer_doc_type("training_deck.txt", "unknown") == "training_material"
    assert _infer_doc_type("ocm_change_plan.txt", "unknown") == "change_management"
    assert _infer_doc_type("comms_newsletter.txt", "unknown") == "comms_plan"
    assert _infer_doc_type("go_live_checklist.txt", "unknown") == "go_live_checklist"
    assert _infer_doc_type("risk_register.txt", "unknown") == "risk_register"
    assert _infer_doc_type("random_document.txt", "my_type") == "my_type"


def test_ingest_with_sharepoint_source_type():
    """Ingest with sharepoint source type uses SharePointConnector (returns empty if no creds)."""
    from ingestion.vector_store import VectorStore
    from registry import RolloutRegistry, RolloutInitiative, DocumentSource
    from tools.ingest import ingest_documents

    store = VectorStore()
    registry = RolloutRegistry()
    registry.register(RolloutInitiative(
        name="SP Rollout",
        sources=[DocumentSource(
            type="sharepoint",
            connection={"site_url": "", "tenant_id": "", "client_id": "", "client_secret": ""},
        )],
    ))

    with patch("tools.ingest.get_vector_store", return_value=store), \
         patch("tools.ingest.get_registry", return_value=registry):
        result = ingest_documents.invoke({"rollout_name": "SP Rollout"})

    # No credentials so no docs fetched — should report 0 docs
    assert "No documents" in result or "Successfully" in result
